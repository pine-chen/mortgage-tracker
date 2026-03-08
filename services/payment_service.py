from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import extract, func
from models import db, Payment, SchedulerConfig


def get_payments(year=None, payment_type=None, page=1, per_page=20):
    """Query payments with optional filters."""
    query = Payment.query.order_by(Payment.date.desc())
    if year:
        query = query.filter(extract('year', Payment.date) == int(year))
    if payment_type:
        query = query.filter(Payment.payment_type == payment_type)
    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_all_payments(year=None, payment_type=None):
    """Query all payments without pagination."""
    query = Payment.query.order_by(Payment.date.desc())
    if year:
        query = query.filter(extract('year', Payment.date) == int(year))
    if payment_type:
        query = query.filter(Payment.payment_type == payment_type)
    return query.all()


def get_payment_by_id(payment_id):
    return db.session.get(Payment, payment_id)


def create_payment(data):
    """Create a new payment record. Returns (payment, amount_changed) tuple."""
    payment = Payment(
        date=data['date'] if isinstance(data['date'], date) else datetime.strptime(data['date'], '%Y-%m-%d').date(),
        amount=Decimal(str(data['amount'])),
        payment_type=data.get('payment_type', 'monthly'),
        notes=data.get('notes', ''),
        source=data.get('source', 'manual'),
        original_id=data.get('original_id'),
    )
    db.session.add(payment)

    amount_changed = False
    if payment.payment_type == 'monthly':
        config = get_or_create_scheduler_config()
        if float(payment.amount) != float(config.current_monthly_amount):
            amount_changed = True

    db.session.commit()
    return payment, amount_changed


def update_payment(payment_id, data):
    """Update an existing payment."""
    payment = db.session.get(Payment, payment_id)
    if not payment:
        return None, False

    if 'date' in data:
        d = data['date']
        payment.date = d if isinstance(d, date) else datetime.strptime(d, '%Y-%m-%d').date()
    if 'amount' in data:
        payment.amount = Decimal(str(data['amount']))
    if 'payment_type' in data:
        payment.payment_type = data['payment_type']
    if 'notes' in data:
        payment.notes = data['notes']

    amount_changed = False
    if payment.payment_type == 'monthly':
        config = get_or_create_scheduler_config()
        if float(payment.amount) != float(config.current_monthly_amount):
            amount_changed = True

    db.session.commit()
    return payment, amount_changed


def delete_payment(payment_id):
    payment = db.session.get(Payment, payment_id)
    if not payment:
        return False
    db.session.delete(payment)
    db.session.commit()
    return True


def get_summary_stats():
    """Calculate aggregate statistics."""
    total = db.session.query(func.sum(Payment.amount)).scalar() or 0
    monthly_total = db.session.query(func.sum(Payment.amount)).filter(
        Payment.payment_type == 'monthly'
    ).scalar() or 0
    monthly_count = Payment.query.filter(Payment.payment_type == 'monthly').count()
    prepayment_total = db.session.query(func.sum(Payment.amount)).filter(
        Payment.payment_type == 'prepayment'
    ).scalar() or 0
    prepayment_count = Payment.query.filter(Payment.payment_type == 'prepayment').count()
    deed_tax_total = db.session.query(func.sum(Payment.amount)).filter(
        Payment.payment_type == 'deed_tax'
    ).scalar() or 0

    config = get_or_create_scheduler_config()

    return {
        'total_amount': float(total),
        'monthly_total': float(monthly_total),
        'monthly_count': monthly_count,
        'prepayment_total': float(prepayment_total),
        'prepayment_count': prepayment_count,
        'deed_tax_total': float(deed_tax_total),
        'current_monthly_amount': float(config.current_monthly_amount),
        'record_count': Payment.query.count(),
    }


def get_monthly_trend():
    """Get monthly payment amounts for trend chart."""
    results = db.session.query(
        extract('year', Payment.date).label('year'),
        extract('month', Payment.date).label('month'),
        Payment.payment_type,
        func.sum(Payment.amount).label('total'),
    ).group_by('year', 'month', Payment.payment_type) \
     .order_by('year', 'month') \
     .all()

    trend = {}
    for row in results:
        key = f"{int(row.year)}-{int(row.month):02d}"
        if key not in trend:
            trend[key] = {'month': key, 'monthly': 0, 'prepayment': 0, 'deed_tax': 0, 'other': 0}
        trend[key][row.payment_type] = float(row.total)

    return list(trend.values())


def get_yearly_stats():
    """Get yearly aggregated stats for bar chart."""
    results = db.session.query(
        extract('year', Payment.date).label('year'),
        Payment.payment_type,
        func.sum(Payment.amount).label('total'),
    ).group_by('year', Payment.payment_type) \
     .order_by('year') \
     .all()

    years = {}
    for row in results:
        y = str(int(row.year))
        if y not in years:
            years[y] = {'year': y, 'monthly': 0, 'prepayment': 0, 'deed_tax': 0, 'other': 0}
        years[y][row.payment_type] = float(row.total)

    return list(years.values())


def get_available_years():
    """Get list of years that have records."""
    results = db.session.query(
        extract('year', Payment.date).label('year')
    ).distinct().order_by(extract('year', Payment.date).desc()).all()
    return [int(r.year) for r in results]


def get_recent_payments(limit=5):
    return Payment.query.order_by(Payment.date.desc()).limit(limit).all()


def get_or_create_scheduler_config():
    config = db.session.get(SchedulerConfig, 1)
    if not config:
        config = SchedulerConfig(id=1)
        db.session.add(config)
        db.session.commit()
    return config


def update_scheduler_config(data):
    config = get_or_create_scheduler_config()
    if 'current_monthly_amount' in data:
        config.current_monthly_amount = Decimal(str(data['current_monthly_amount']))
    if 'payment_day' in data:
        config.payment_day = int(data['payment_day'])
    if 'is_enabled' in data:
        config.is_enabled = bool(data['is_enabled'])
    db.session.commit()
    return config


def check_monthly_exists(year, month):
    """Check if a monthly payment already exists for given year/month."""
    return Payment.query.filter(
        Payment.payment_type == 'monthly',
        extract('year', Payment.date) == year,
        extract('month', Payment.date) == month,
    ).first() is not None
