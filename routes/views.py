from flask import render_template, request, redirect, url_for, flash
from . import views_bp
from services import payment_service
from models import Payment


@views_bp.route('/')
def index():
    stats = payment_service.get_summary_stats()
    trend = payment_service.get_monthly_trend()
    yearly = payment_service.get_yearly_stats()
    recent = payment_service.get_recent_payments(5)

    # Type distribution for pie chart
    type_dist = {
        '月供': stats['monthly_total'],
        '提前还款': stats['prepayment_total'],
        '契税': stats['deed_tax_total'],
    }

    return render_template('index.html',
                           stats=stats, trend=trend, yearly=yearly,
                           recent=recent, type_dist=type_dist)


@views_bp.route('/records')
def records():
    year = request.args.get('year', type=int)
    payment_type = request.args.get('type')
    page = request.args.get('page', 1, type=int)
    pagination = payment_service.get_payments(year=year, payment_type=payment_type, page=page, per_page=15)
    years = payment_service.get_available_years()
    return render_template('records.html',
                           pagination=pagination, years=years,
                           current_year=year, current_type=payment_type,
                           payment_types=Payment.TYPES)


@views_bp.route('/records/add', methods=['POST'])
def add_record():
    data = {
        'date': request.form['date'],
        'amount': request.form['amount'],
        'payment_type': request.form['payment_type'],
        'notes': request.form.get('notes', ''),
        'source': 'manual',
    }
    payment, amount_changed = payment_service.create_payment(data)
    if amount_changed:
        flash(f'记录已添加。检测到月供金额变更（当前配置: {payment_service.get_or_create_scheduler_config().current_monthly_amount}），'
              f'请前往设置页更新自动记账金额。', 'warning')
    else:
        flash('记录已添加', 'success')
    return redirect(url_for('views.records'))


@views_bp.route('/records/<int:payment_id>/edit', methods=['POST'])
def edit_record(payment_id):
    data = {
        'date': request.form['date'],
        'amount': request.form['amount'],
        'payment_type': request.form['payment_type'],
        'notes': request.form.get('notes', ''),
    }
    payment, amount_changed = payment_service.update_payment(payment_id, data)
    if not payment:
        flash('记录不存在', 'danger')
    elif amount_changed:
        flash(f'记录已更新。检测到月供金额变更，请前往设置页更新自动记账金额。', 'warning')
    else:
        flash('记录已更新', 'success')
    return redirect(url_for('views.records'))


@views_bp.route('/records/<int:payment_id>/delete', methods=['POST'])
def delete_record(payment_id):
    if payment_service.delete_payment(payment_id):
        flash('记录已删除', 'success')
    else:
        flash('记录不存在', 'danger')
    return redirect(url_for('views.records'))


@views_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_scheduler':
            payment_service.update_scheduler_config({
                'current_monthly_amount': request.form['monthly_amount'],
                'payment_day': request.form['payment_day'],
                'is_enabled': 'is_enabled' in request.form,
            })
            flash('定时任务配置已更新', 'success')
        elif action == 'import_csv':
            file = request.files.get('csv_file')
            if file and file.filename.endswith('.csv'):
                import tempfile, os
                fd, tmp_path = tempfile.mkstemp(suffix='.csv')
                file.save(tmp_path)
                os.close(fd)
                try:
                    from import_csv import import_csv_file
                    count = import_csv_file(tmp_path)
                    flash(f'成功导入 {count} 条记录', 'success')
                finally:
                    os.unlink(tmp_path)
            else:
                flash('请上传 CSV 文件', 'danger')
        return redirect(url_for('views.settings'))

    config = payment_service.get_or_create_scheduler_config()
    return render_template('settings.html', config=config)
