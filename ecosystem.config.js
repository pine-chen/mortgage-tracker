module.exports = {
  apps: [
    {
      name: 'mortgage-tracker',
      script: './venv/bin/gunicorn',
      args: '-w 1 -b 127.0.0.1:5001 --access-logfile logs/access.log "app:create_app()"',
      cwd: __dirname,
      interpreter: 'none',          // gunicorn is already an executable
      env_file: '.env',             // auto-load .env
      watch: false,
      max_restarts: 10,
      restart_delay: 3000,          // 3s between restarts
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
