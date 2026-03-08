import logging
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def auto_record_monthly(app):
    """Check and create automatic monthly payment record."""
    with app.app_context():
        from services.payment_service import (
            get_or_create_scheduler_config,
            check_monthly_exists,
            create_payment,
        )
        from models import db

        config = get_or_create_scheduler_config()
        if not config.is_enabled:
            logger.info("Scheduler disabled, skipping.")
            return

        today = date.today()
        if today.day != config.payment_day:
            logger.info(f"Today is day {today.day}, payment day is {config.payment_day}. Skipping.")
            return

        if check_monthly_exists(today.year, today.month):
            logger.info(f"Monthly payment for {today.year}-{today.month:02d} already exists. Skipping.")
            return

        payment, _ = create_payment({
            'date': today,
            'amount': float(config.current_monthly_amount),
            'payment_type': 'monthly',
            'notes': '自动记账',
            'source': 'auto',
        })
        config.last_run_at = datetime.now()
        db.session.commit()
        logger.info(f"Auto-recorded monthly payment: {float(config.current_monthly_amount)} on {today}")


def init_scheduler(app):
    """Initialize APScheduler with the Flask app."""
    if scheduler.running:
        return

    trigger = CronTrigger(
        hour=app.config.get('SCHEDULER_CHECK_HOUR', 8),
        minute=app.config.get('SCHEDULER_CHECK_MINUTE', 0),
    )

    scheduler.add_job(
        auto_record_monthly,
        trigger=trigger,
        args=[app],
        id='auto_monthly_payment',
        replace_existing=True,
        misfire_grace_time=86400,
    )
    scheduler.start()
    logger.info("APScheduler started.")
