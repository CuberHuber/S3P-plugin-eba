# S3P-plugin-eba



## Config

```json
{
  "payload": {
    "file": "eba.py",
    "class": "Eba",
    "entry": {
        "point": "content",
        "params": [
          {"key": "webdriver", "value": {"type": "module", "name": "WebDriver", "bus": true}},
          {"key": "max_count_documents", "value": {"type": "const", "name": 9999}},
          {"key": "last_document", "value": {"type": "module", "name": "LastDocumentBySrc", "bus": true, "params": {}}}, 
          {"key": "webdriverwait", "value": {"type": "const", "name": 20}},
          {"key": "isextracttext", "value": {"type": "const", "name": false}}
        ]
    }
  } 
}
```

Параметры парсера:
- `webdriverwait` - задержка для waitdriver
- `isextracttext` - Флаг, нужно ли парсеру извлекать текст из pdf документа