# Публикация отдельного репозитория

Рекомендуемое имя: `orbit-launcher`.

Описание: `Keyboard-first Windows launcher built with Python, PySide6 and SQLite. Search, favorites, global hotkeys and a safe calculator.`

Темы: `python`, `pyside6`, `windows`, `launcher`, `desktop-app`, `sqlite`, `portfolio`.

1. Создайте пустой репозиторий GitHub без автоматического README.
2. Распакуйте архив исходников в отдельную папку вне существующего учебного Git-репозитория.
3. Откройте терминал в этой папке и выполните:

```powershell
git init
git add .
git commit -m "Initial release: Orbit Launcher"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/orbit-launcher.git
git push -u origin main
```

Замените `YOUR_USERNAME`. Агент не выполняет эти команды и не публикует репозиторий.
Не загружайте `.venv`, `build`, `dist`, рабочие базы и личные экспорты.
Сборку Windows можно приложить к GitHub Release отдельным ZIP, не добавляя её в исходники.

После публикации проверьте отображение изображений в README и результаты Actions.
