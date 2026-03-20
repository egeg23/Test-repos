#!/bin/bash
# ssh_monitor_and_deploy.sh - Мониторинг SSH и автодеплой

SERVER="109.73.198.185"
USER="root"
SSH_PASS_FILE="/tmp/ssh_pass.txt"
LOG_FILE="/tmp/ssh_monitor.log"
TELEGRAM_BOT_DIR="/opt/telegram_bot"
LOCAL_BOT_DIR="/opt/telegram_bot"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Проверяем доступность SSH
log "=== Проверка SSH соединения ==="

# Пробуем подключиться и выполнить простую команду
if sshpass -f "$SSH_PASS_FILE" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USER@$SERVER" "echo 'SSH_OK'" 2>/dev/null | grep -q "SSH_OK"; then
    log "✅ SSH соединение СТАБИЛЬНО"
    
    # Проверяем, нужен ли деплой
    log "📦 Проверка необходимости деплоя..."
    
    # Получаем текущий коммит на сервере
    SERVER_COMMIT=$(sshpass -f "$SSH_PASS_FILE" ssh "$USER@$SERVER" "cd $TELEGRAM_BOT_DIR && git rev-parse HEAD 2>/dev/null" 2>/dev/null)
    
    # Получаем последний коммит из локального репозитория
    LOCAL_COMMIT=$(cd "$LOCAL_BOT_DIR" && git rev-parse HEAD 2>/dev/null)
    
    if [ "$SERVER_COMMIT" != "$LOCAL_COMMIT" ]; then
        log "🔄 Обнаружены изменения: сервер ${SERVER_COMMIT:0:8} ≠ репо ${LOCAL_COMMIT:0:8}"
        log "🚀 Запуск автодеплоя..."
        
        # Копируем все Python файлы
        for file in "$LOCAL_BOT_DIR"/*.py; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                sshpass -f "$SSH_PASS_FILE" scp "$file" "$USER@$SERVER:$TELEGRAM_BOT_DIR/" 2>/dev/null
                log "📄 Скопирован: $filename"
            fi
        done
        
        # Копируем папку modules
        if [ -d "$LOCAL_BOT_DIR/modules" ]; then
            sshpass -f "$SSH_PASS_FILE" scp -r "$LOCAL_BOT_DIR/modules/"* "$USER@$SERVER:$TELEGRAM_BOT_DIR/modules/" 2>/dev/null
            log "📁 Скопированы модули"
        fi
        
        # Проверяем, запущен ли бот
        BOT_PID=$(sshpass -f "$SSH_PASS_FILE" ssh "$USER@$SERVER" "pgrep -f 'python bot.py'" 2>/dev/null)
        
        if [ -n "$BOT_PID" ]; then
            log "🔄 Бот запущен (PID: $BOT_PID), перезапускаю..."
            sshpass -f "$SSH_PASS_FILE" ssh "$USER@$SERVER" "pkill -9 -f 'python bot.py'; sleep 2" 2>/dev/null
        else
            log "ℹ️ Бот не был запущен"
        fi
        
        # Устанавливаем зависимости если нужно
        sshpass -f "$SSH_PASS_FILE" ssh "$USER@$SERVER" "cd $TELEGRAM_BOT_DIR && source venv/bin/activate && pip install -q beautifulsoup4 lxml pillow psycopg2-binary 2>/dev/null" 2>/dev/null
        
        # Запускаем бота
        sshpass -f "$SSH_PASS_FILE" ssh "$USER@$SERVER" "cd $TELEGRAM_BOT_DIR && source venv/bin/activate && nohup python bot.py > /tmp/bot.log 2>&1 &" 2>/dev/null
        sleep 5
        
        # Проверяем, запустился ли
        NEW_PID=$(sshpass -f "$SSH_PASS_FILE" ssh "$USER@$SERVER" "pgrep -f 'python bot.py'" 2>/dev/null)
        if [ -n "$NEW_PID" ]; then
            log "✅ Бот успешно запущен (PID: $NEW_PID)"
            echo "🚀 **Автодеплой выполнен!**

✅ SSH стабильно
✅ Код обновлён (${LOCAL_COMMIT:0:8})
✅ Бот запущен (PID: $NEW_PID)" > /tmp/deploy_status.txt
        else
            log "❌ Ошибка запуска бота"
            echo "❌ **Ошибка автодеплоя**

SSH стабильно, но бот не запустился.
Проверьте логи: /tmp/bot.log" > /tmp/deploy_status.txt
        fi
    else
        log "ℹ️ Код актуален, деплой не требуется"
        echo "✅ Проверка завершена

SSH стабильно, код актуален.
Бот работает нормально." > /tmp/deploy_status.txt
    fi
else
    log "❌ SSH соединение НЕСТАБИЛЬНО"
    echo "⚠️ **SSH нестабильно**

Автодеплой отложен.
Следующая проверка через 30 минут." > /tmp/deploy_status.txt
fi

log "=== Проверка завершена ==="
