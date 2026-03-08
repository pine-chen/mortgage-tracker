#!/usr/bin/env python3
"""Import mortgage payment records from QianJi CSV export."""

import sys
import pandas as pd
from datetime import datetime
from decimal import Decimal


def import_csv_file(csv_path):
    """Import CSV file and return number of records imported."""
    from app import create_app
    from models import db, Payment, SchedulerConfig

    app = create_app()
    count = 0

    with app.app_context():
        df = pd.read_csv(csv_path, encoding='utf-8')
        latest_monthly_amount = None

        for _, row in df.iterrows():
            original_id = str(row['ID']).strip() if pd.notna(row.get('ID')) else None
            if not original_id:
                continue

            # Skip if already imported
            if Payment.query.filter_by(original_id=original_id).first():
                continue

            notes = str(row.get('备注', '')).strip() if pd.notna(row.get('备注')) else ''
            amount = float(row['金额'])

            # Classify by notes
            if '提前还款' in notes:
                payment_type = 'prepayment'
            elif '契税' in notes:
                payment_type = 'deed_tax'
            else:
                payment_type = 'monthly'

            date_str = str(row['时间']).strip()
            payment_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').date()

            payment = Payment(
                date=payment_date,
                amount=Decimal(str(amount)),
                payment_type=payment_type,
                notes=notes,
                source='import',
                original_id=original_id,
            )
            db.session.add(payment)
            count += 1

            # Track latest monthly amount for scheduler config
            if payment_type == 'monthly':
                if latest_monthly_amount is None or payment_date > latest_monthly_amount[1]:
                    latest_monthly_amount = (amount, payment_date)

        db.session.commit()

        # Update scheduler config with latest monthly amount
        if latest_monthly_amount:
            config = db.session.get(SchedulerConfig, 1)
            if not config:
                config = SchedulerConfig(id=1)
                db.session.add(config)
            config.current_monthly_amount = Decimal(str(latest_monthly_amount[0]))
            db.session.commit()

    return count


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_csv.py <csv_file_path>")
        sys.exit(1)

    csv_path = sys.argv[1]
    count = import_csv_file(csv_path)
    print(f"Successfully imported {count} records.")
