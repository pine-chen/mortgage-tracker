from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Payment(db.Model):
    __tablename__ = 'payment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(20), nullable=False, default='monthly')
    notes = db.Column(db.Text, default='')
    source = db.Column(db.String(20), nullable=False, default='manual')
    original_id = db.Column(db.String(64), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    TYPES = {
        'monthly': '月供',
        'prepayment': '提前还款',
        'deed_tax': '契税',
        'other': '其他',
    }

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'amount': float(self.amount),
            'payment_type': self.payment_type,
            'payment_type_label': self.TYPES.get(self.payment_type, self.payment_type),
            'notes': self.notes or '',
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SchedulerConfig(db.Model):
    __tablename__ = 'scheduler_config'

    id = db.Column(db.Integer, primary_key=True, default=1)
    current_monthly_amount = db.Column(db.Numeric(10, 2), nullable=False, default=4230.0)
    payment_day = db.Column(db.Integer, nullable=False, default=18)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_run_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'current_monthly_amount': float(self.current_monthly_amount),
            'payment_day': self.payment_day,
            'is_enabled': self.is_enabled,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
        }
