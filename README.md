# 🤖 Seller AI Bot

Автономная система управления продажами на маркетплейсах (Wildberries, Ozon, Авито).

## 🐰 CodeRabbit Integration

Этот репозиторий использует **CodeRabbit** для автоматического code review.

### Как работает

1. **Создаёшь PR** → CodeRabbit автоматически проверяет код
2. **CodeRabbit комментирует** → находит ошибки, баги, уязвимости
3. **Kimi (AI) проверяет** → тестирует на сервере
4. **Ты аппрувишь** → нажимаешь Merge

### Ссылки

- [Pull Requests](https://github.com/egeg23/Test-repos/pulls)
- [CodeRabbit Config](.coderabbit.yaml)
- [Workflow Docs](CODERABBIT_WORKFLOW.md)

## 🏗 Архитектура

```
/opt/telegram_bot/
├── bot.py                    # Telegram bot entry point
├── modules/
│   ├── AUTONOMOUS_BRAIN.py   # Autonomy core
│   ├── INTEGRATION_LAYER.py  # API integrations (WB, Ozon)
│   ├── MPSTATS_COLLECTOR.py  # Competitor analysis
│   └── ...
└── scripts/
    └── check_prs.sh          # PR monitoring
```

## 🚀 Быстрый старт

```bash
# Проверка новых PR
./scripts/check_prs.sh
```

## 🔒 Безопасность

- Никаких токенов в коде
- Все credentials в `/opt/clients/` (не в git)
- CodeRabbit проверяет уязвимости автоматически