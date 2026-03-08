#!/bin/bash
# mortgage-tracker deploy script (PM2 + Gunicorn)
# Usage: ./deploy.sh [init|update|start|stop|restart|status|backup|logs|import]

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
APP_NAME="mortgage-tracker"

# Load .env if exists
if [ -f "$APP_DIR/.env" ]; then
    set -a
    source "$APP_DIR/.env"
    set +a
fi

ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtualenv..."
        python3 -m venv "$VENV_DIR"
    fi
    source "$VENV_DIR/bin/activate"
}

case "${1:-help}" in
    init)
        echo "=== Initializing $APP_NAME ==="
        ensure_venv
        pip install -r "$APP_DIR/requirements.txt"

        # Create .env template if not exists
        if [ ! -f "$APP_DIR/.env" ]; then
            cat > "$APP_DIR/.env" <<'EOF'
SECRET_KEY=change-me-to-random-string
MORTGAGE_API_KEY=change-me-your-api-key

# Web UI login (leave empty to disable)
MORTGAGE_WEB_USER=admin
MORTGAGE_WEB_PASS=change-me

# TG whitelist: comma-separated user IDs for auto-login tokens
TG_WHITELIST=1308785881

# Scheduler: 1=enable, 0=disable (disable if running multiple workers)
SCHEDULER_ENABLED=1
EOF
            echo "Created .env — please edit it with your values"
        fi

        # Check PM2
        if ! command -v pm2 &>/dev/null; then
            echo "WARNING: pm2 not found. Install with: npm install -g pm2"
        fi

        echo "=== Done. Next: edit .env, then run: ./deploy.sh start ==="
        ;;

    update)
        echo "=== Updating $APP_NAME ==="
        cd "$APP_DIR"
        git pull
        ensure_venv
        pip install -r requirements.txt
        echo "=== Updated. Run: ./deploy.sh restart ==="
        ;;

    start)
        ensure_venv
        cd "$APP_DIR"
        echo "=== Starting $APP_NAME via PM2 ==="
        pm2 start ecosystem.config.js
        pm2 save
        echo "=== Started. Run 'pm2 status' to verify ==="
        ;;

    stop)
        echo "=== Stopping $APP_NAME ==="
        pm2 stop "$APP_NAME" 2>/dev/null || echo "Not running."
        ;;

    restart)
        ensure_venv
        cd "$APP_DIR"
        echo "=== Restarting $APP_NAME ==="
        pm2 restart ecosystem.config.js --update-env
        pm2 save
        ;;

    status)
        pm2 show "$APP_NAME" 2>/dev/null || echo "$APP_NAME is not running."
        ;;

    backup)
        BACKUP_DIR="$APP_DIR/backups"
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="$BACKUP_DIR/mortgage_$(date +%Y%m%d_%H%M%S).db"
        cp "$APP_DIR/data/mortgage.db" "$BACKUP_FILE"
        echo "Backup saved: $BACKUP_FILE"
        # Keep only last 10 backups
        ls -t "$BACKUP_DIR"/mortgage_*.db | tail -n +11 | xargs rm -f 2>/dev/null
        echo "Backups retained: $(ls "$BACKUP_DIR"/mortgage_*.db | wc -l)"
        ;;

    logs)
        pm2 logs "$APP_NAME" --lines 50
        ;;

    import)
        if [ -z "$2" ]; then
            echo "Usage: ./deploy.sh import /path/to/file.csv"
            exit 1
        fi
        ensure_venv
        cd "$APP_DIR"
        python import_csv.py "$2"
        ;;

    help|*)
        echo "Usage: ./deploy.sh {init|update|start|stop|restart|status|backup|logs|import <csv>}"
        echo ""
        echo "  init     - Create venv, install deps, generate .env template"
        echo "  update   - Git pull + reinstall deps"
        echo "  start    - Start via PM2 (Gunicorn, single worker)"
        echo "  stop     - Stop PM2 process"
        echo "  restart  - Restart + reload .env"
        echo "  status   - Show PM2 process info"
        echo "  backup   - Backup SQLite database"
        echo "  logs     - Show PM2 logs (realtime)"
        echo "  import   - Import CSV file"
        ;;
esac
