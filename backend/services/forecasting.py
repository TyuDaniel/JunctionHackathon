"""
Demand Forecasting Engine
Uses scikit-learn RandomForest to predict charging demand per site
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import os

from backend.models.session import ChargingSession
from backend.models.forecast import DemandForecast


class DemandForecaster:
    """
    ML-based demand forecasting using Random Forest
    """
    
    def __init__(self, model_path: str = "models/demand_forecast.pkl"):
        self.model_path = model_path
        self.model = None
        self.site_encoder = LabelEncoder()
        self.feature_cols = [
            'hour_of_day', 'day_of_week', 'is_weekend', 'is_holiday',
            'temperature', 'site_encoded', 'historical_avg_kwh',
            'historical_session_count'
        ]
        
    def prepare_features(
        self,
        sessions_df: pd.DataFrame,
        target_hours: Optional[List[datetime]] = None
    ) -> pd.DataFrame:
        """
        Prepare features for training or prediction
        
        Args:
            sessions_df: DataFrame with historical charging sessions
            target_hours: If provided, generate features for these specific hours
        
        Returns:
            DataFrame with engineered features
        """
        
        if target_hours:
            # Generate features for prediction
            features = []
            for target_time in target_hours:
                for site_id in sessions_df['site_id'].unique():
                    # Get historical data for this site
                    site_sessions = sessions_df[sessions_df['site_id'] == site_id]
                    
                    # Calculate historical averages (last 7 days)
                    recent = site_sessions[
                        (site_sessions['start_time'] >= target_time - timedelta(days=7)) &
                        (site_sessions['start_time'] < target_time)
                    ]
                    
                    hist_avg_kwh = recent['energy_delivered_kwh'].mean() if len(recent) > 0 else 0
                    hist_session_count = len(recent) / 7  # avg per day
                    
                    features.append({
                        'time_slot': target_time,
                        'site_id': site_id,
                        'hour_of_day': target_time.hour,
                        'day_of_week': target_time.weekday(),
                        'is_weekend': 1 if target_time.weekday() >= 5 else 0,
                        'is_holiday': 0,  # Simplified for hackathon
                        'temperature': self._simulate_temperature(target_time),
                        'historical_avg_kwh': hist_avg_kwh,
                        'historical_session_count': hist_session_count
                    })
            
            features_df = pd.DataFrame(features)
        else:
            # Aggregate sessions by site and hour for training
            sessions_df['hour'] = pd.to_datetime(sessions_df['start_time']).dt.floor('H')
            
            # Group by site and hour
            aggregated = sessions_df.groupby(['site_id', 'hour']).agg({
                'energy_delivered_kwh': 'sum',
                'id': 'count'
            }).reset_index()
            
            aggregated.columns = ['site_id', 'time_slot', 'total_kwh', 'session_count']
            
            # Add time-based features
            aggregated['hour_of_day'] = pd.to_datetime(aggregated['time_slot']).dt.hour
            aggregated['day_of_week'] = pd.to_datetime(aggregated['time_slot']).dt.dayofweek
            aggregated['is_weekend'] = (aggregated['day_of_week'] >= 5).astype(int)
            aggregated['is_holiday'] = 0  # Simplified
            
            # Add simulated temperature
            aggregated['temperature'] = aggregated['time_slot'].apply(self._simulate_temperature)
            
            # Add historical features (rolling averages)
            for site_id in aggregated['site_id'].unique():
                mask = aggregated['site_id'] == site_id
                aggregated.loc[mask, 'historical_avg_kwh'] = (
                    aggregated.loc[mask, 'total_kwh'].rolling(window=24*7, min_periods=1).mean()
                )
                aggregated.loc[mask, 'historical_session_count'] = (
                    aggregated.loc[mask, 'session_count'].rolling(window=24*7, min_periods=1).mean()
                )
            
            features_df = aggregated
        
        return features_df
    
    def _simulate_temperature(self, dt: datetime) -> float:
        """
        Simulate temperature based on time of day and season
        In production, would use actual weather API
        """
        # Base temperature varies by month (simplified)
        month_base = {
            1: 0, 2: -2, 3: 3, 4: 8, 5: 14, 6: 18,
            7: 20, 8: 19, 9: 14, 10: 8, 11: 3, 12: 1
        }
        base = month_base.get(dt.month, 10)
        
        # Variation by hour of day
        hour_variation = np.sin((dt.hour - 6) * np.pi / 12) * 5
        
        return base + hour_variation
    
    def train(
        self,
        db: Session,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict[str, float]:
        """
        Train the demand forecasting model
        
        Args:
            db: Database session
            test_size: Proportion of data for testing
            random_state: Random seed for reproducibility
        
        Returns:
            Dictionary with training metrics (R2, MAE, RMSE)
        """
        
        # Load historical sessions
        sessions = db.query(ChargingSession).filter(
            ChargingSession.status == 'completed',
            ChargingSession.energy_delivered_kwh.isnot(None)
        ).all()
        
        if len(sessions) < 100:
            raise ValueError("Insufficient training data. Need at least 100 completed sessions.")
        
        # Convert to DataFrame
        sessions_data = []
        for s in sessions:
            sessions_data.append({
                'id': s.id,
                'site_id': s.site_id,
                'start_time': s.start_time,
                'energy_delivered_kwh': s.energy_delivered_kwh or 0
            })
        
        sessions_df = pd.DataFrame(sessions_data)
        
        # Prepare features
        features_df = self.prepare_features(sessions_df)
        
        # Encode site_id
        features_df['site_encoded'] = self.site_encoder.fit_transform(features_df['site_id'])
        
        # Prepare X and y
        X = features_df[self.feature_cols]
        y = features_df['total_kwh'] if 'total_kwh' in features_df.columns else features_df['energy_delivered_kwh']
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        # Train Random Forest
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        y_pred = self.model.predict(X_test)
        mae = np.mean(np.abs(y_test - y_pred))
        rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'site_encoder': self.site_encoder,
            'feature_cols': self.feature_cols
        }, self.model_path)
        
        return {
            'train_r2': round(train_score, 4),
            'test_r2': round(test_score, 4),
            'mae': round(mae, 4),
            'rmse': round(rmse, 4)
        }
    
    def load_model(self) -> bool:
        """
        Load trained model from disk
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.model_path):
            return False
        
        try:
            saved = joblib.load(self.model_path)
            self.model = saved['model']
            self.site_encoder = saved['site_encoder']
            self.feature_cols = saved['feature_cols']
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict(
        self,
        site_id: str,
        target_time: datetime,
        db: Session,
        hours_ahead: int = 24
    ) -> List[Dict]:
        """
        Predict demand for a site over the next N hours
        
        Args:
            site_id: Site identifier
            target_time: Starting time for predictions
            db: Database session
            hours_ahead: Number of hours to predict
        
        Returns:
            List of predictions with confidence intervals
        """
        
        if self.model is None:
            if not self.load_model():
                raise ValueError("Model not trained. Please train the model first.")
        
        # Generate target hours
        target_hours = [target_time + timedelta(hours=i) for i in range(hours_ahead)]
        
        # Load recent historical sessions for feature engineering
        lookback = target_time - timedelta(days=7)
        sessions = db.query(ChargingSession).filter(
            ChargingSession.site_id == site_id,
            ChargingSession.start_time >= lookback,
            ChargingSession.start_time < target_time,
            ChargingSession.energy_delivered_kwh.isnot(None)
        ).all()
        
        sessions_data = []
        for s in sessions:
            sessions_data.append({
                'id': s.id,
                'site_id': s.site_id,
                'start_time': s.start_time,
                'energy_delivered_kwh': s.energy_delivered_kwh or 0
            })
        
        sessions_df = pd.DataFrame(sessions_data) if sessions_data else pd.DataFrame({
            'id': [], 'site_id': [], 'start_time': [], 'energy_delivered_kwh': []
        })
        
        # If no historical data, use dummy data
        if len(sessions_df) == 0:
            sessions_df = pd.DataFrame({
                'id': ['dummy'],
                'site_id': [site_id],
                'start_time': [lookback],
                'energy_delivered_kwh': [0]
            })
        
        # Prepare features
        features_df = self.prepare_features(sessions_df, target_hours)
        
        # Encode site_id
        if site_id in self.site_encoder.classes_:
            features_df['site_encoded'] = self.site_encoder.transform([site_id] * len(features_df))
        else:
            # Unknown site, use mean encoding
            features_df['site_encoded'] = 0
        
        # Make predictions
        X = features_df[self.feature_cols]
        predictions = self.model.predict(X)
        
        # Estimate confidence intervals using tree variance
        # Get predictions from all trees
        all_tree_predictions = np.array([tree.predict(X) for tree in self.model.estimators_])
        std_predictions = np.std(all_tree_predictions, axis=0)
        
        # Build results
        results = []
        for i, (time_slot, pred, std) in enumerate(zip(target_hours, predictions, std_predictions)):
            # Estimate session count (simplified heuristic)
            avg_kwh_per_session = 30  # Approximate average
            predicted_sessions = max(1, int(pred / avg_kwh_per_session))
            
            results.append({
                'time_slot': time_slot,
                'predicted_total_kwh': max(0, round(pred, 2)),
                'predicted_active_sessions': predicted_sessions,
                'confidence_lower': max(0, round(pred - 1.96 * std, 2)),
                'confidence_upper': round(pred + 1.96 * std, 2)
            })
        
        return results
    
    def save_forecasts_to_db(
        self,
        forecasts: List[Dict],
        site_id: str,
        db: Session,
        model_version: str = "v1.0"
    ):
        """
        Save predictions to database
        """
        for forecast in forecasts:
            forecast_id = f"{site_id}_{forecast['time_slot'].strftime('%Y%m%d%H')}"
            
            db_forecast = DemandForecast(
                id=forecast_id,
                site_id=site_id,
                time_slot=forecast['time_slot'],
                predicted_total_kwh=forecast['predicted_total_kwh'],
                predicted_active_sessions=forecast['predicted_active_sessions'],
                confidence_lower=forecast['confidence_lower'],
                confidence_upper=forecast['confidence_upper'],
                model_version=model_version
            )
            
            # Merge to handle duplicates
            db.merge(db_forecast)
        
        db.commit()

