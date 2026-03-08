#!/bin/bash
# mortgage-tracker deploy script
# Usage: ./deploy.sh [init|update|start|stop|restart|status|backup|logs]

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
APP_NAME="mortgage-tracker"
PORT=5001
BIND="127.0.0.1:$PORT"

# Load .env if exists
if [ -f "$APP_DIR/.env" ]; then
    export $(grep -v '^#' "$APP_DIR/.env" | xargs)
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

# Scheduler: 1=enable, 0=disable (disable if running multiple workers)
SCHEDULER_ENABLED=1
EOF
            echo "Created .env — please edit it with your values"
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
        echo "=== Starting $APP_NAME on $BIND ==="
        # Single worker (scheduler safe), preload app
        cd "$APP_DIR"
        gunicorn \
            -w 1 \
            -b "$BIND" \
            --access-logfile "$APP_DIR/logs/access.log" \
            --error-logfile "$APP_DIR/logs/error.log" \
            --pid "$APP_DIR/data/gunicorn.pid" \
            --daemon \
            "app:create_app()"
        echo "Started. PID: $(cat "$APP_DIR/data/gunicorn.pid")"
        ;;

    stop)
        if [ -f "$APP_DIR/data/gunicorn.pid" ]; then
            echo "=== Stopping $APP_NAME ==="
            kill $(cat "$APP_DIR/data/gunicorn.pid") 2>/dev/null || true
            rm -f "$APP_DIR/data/gunicorn.pid"
            echo "Stopped."
        else
            echo "Not running (no PID file)."
        fi
        ;;

    restart)
        $0 stop
        sleep 1
        $0 start
        ;;

    status)
        if [ -f "$APP_DIR/data/gunicorn.pid" ] && kill -0 $(cat "$APP_DIR/data/gunicorn.pid") 2>/dev/null; then
            echo "$APP_NAME is running (PID: $(cat "$APP_DIR/data/gunicorn.pid"))"
        else
            echo "$APP_NAME is not running."
        fi
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
        tail -f "$APP_DIR/logs/app.log" "$APP_DIR/logs/access.log"
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
        echo "  start    - Start Gunicorn (daemon, single worker)"
        echo "  stop     - Stop Gunicorn"
        echo "  restart  - Stop + Start"
        echo "  status   - Check if running"
        echo "  backup   - Backup SQLite database"
        echo "  logs     - Tail application logs"
        echo "  import   - Import CSV file"
        ;;
esac
