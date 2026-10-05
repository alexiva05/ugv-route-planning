# Контейнер ВКР

Рабочий контейнер и образ: `isaac-lab-base-vkr`. Compose-проект: `ugv-vkr`.
Запуск использует штатный `IsaacLab/docker/container.py`, профиль `base`,
`--suffix vkr` и единственное дополнение `compose.vkr.yaml`.
Контейнер собирается из Dockerfile Isaac Lab и не требует другого запущенного контейнера.

Проверенный checkout Isaac Lab: `v3.0.0-EA`, коммит
`ae37b028ea415c91ea2bc32609efcd759ed2b974`.
В его `docker/.env.base` задан Isaac Sim `6.1.0`.
Пользователь образа имеет UID/GID 1000, совпадающие с владельцем каталогов
на текущем хосте. На другом компьютере нужно проверить права на эти каталоги.

## Каталоги

Репозитории и данные расположены рядом:

```text
~/robotics/
├── IsaacLab/
├── ugv-route-planning/
└── research-data/
```

| Каталог хоста | Путь в контейнере |
| --- | --- |
| `ugv-route-planning/` | `/workspace/ugv-route-planning` |
| `research-data/` | `/workspace/research-data` |
| `IsaacLab/source/` | `/workspace/isaaclab/source` |
| `IsaacLab/scripts/` | `/workspace/isaaclab/scripts` |
| `IsaacLab/docs/` | `/workspace/isaaclab/docs` |
| `IsaacLab/tools/` | `/workspace/isaaclab/tools` |

Все перечисленные подключения разрешают чтение и запись. Весь каталог
IsaacLab целиком не монтируется: остальные файлы находятся в образе.
Результаты экспериментов сохраняйте в `/workspace/research-data/runs/`.
Кэши, служебные данные и стандартные журналы Isaac Lab/Isaac Sim находятся
в отдельных именованных томах Docker с префиксом `ugv-vkr_`.

## Создание или обновление контейнера

На хосте нужны Docker с Compose, NVIDIA Container Toolkit, драйвер NVIDIA
и графическая сессия с доступным X11. На текущей машине проверялся `DISPLAY=:1`;
при запуске используйте значение текущей сессии, не задавайте его жёстко.

В терминале Ubuntu, вне контейнера:

```bash
cd "$HOME/robotics/IsaacLab"
./docker/container.py start base \
  --files ../../ugv-route-planning/docker/compose.vkr.yaml \
  --suffix vkr
```

При первом запросе X11 forwarding ответьте `y`. Настройка хранится локально
в `IsaacLab/docker/.container.cfg`. Скрипт подключает X11 и файл авторизации;
GPU подключается штатным Compose-файлом Isaac Lab.
`start` может пересобрать образ и пересоздать контейнер; изменения,
сделанные только внутри файловой системы контейнера, при этом теряются.
Bind mounts и именованные тома сохраняются.

Посмотреть конфигурацию без создания контейнера:

```bash
./docker/container.py config base \
  --files ../../ugv-route-planning/docker/compose.vkr.yaml \
  --suffix vkr
```

Команда `config` показывает основные настройки; X11-файл штатный помощник
добавляет отдельно при `start`.

## Вход и GUI

На хосте:

```bash
cd "$HOME/robotics/IsaacLab"
./docker/container.py enter base --suffix vkr
```

Внутри контейнера:

```bash
/workspace/ugv-route-planning/scripts/gui.sh
```

Сценарий запускает пример `create_empty.py` через Python Isaac Sim и
AppLauncher, с визуализацией Kit. Он также включает `omni.kit.menu.file`,
чтобы меню **File → Save As…** было доступно при каждом таком запуске.
Наличие меню зависит от успешной загрузки расширения; ошибки видны в консоли.

Зависимости этой Docker-сборки установлены в Python Isaac Sim. `uv` для
этого запуска не требуется. Для собственного Python-сценария, использующего
AppLauncher, команда имеет вид:

```bash
cd /workspace/isaaclab
/isaac-sim/python.sh /workspace/ugv-route-planning/scripts/ИМЯ_СКРИПТА.py \
  --viz kit --kit_args="--enable omni.kit.menu.file"
```

Замените `ИМЯ_СКРИПТА.py` именем существующего сценария.

## Проверка данных

Внутри контейнера:

```bash
nvidia-smi
ls -lah /workspace/research-data/assets/ugv/working
```

В GUI загрузите модель из этого каталога. Для проверки записи используйте
**File → Save As…** и сохраните копию под новым именем, например
`/workspace/research-data/assets/ugv/working/ugv_save_test.usd`.
На хосте файл появится в `~/robotics/research-data/assets/ugv/working/`.

Пользователь подтвердил запуск GUI, загрузку модели и появление сохранённого
USD-файла на хосте. В той сессии меню File включалось через Script Editor;
`gui.sh` закрепляет включение того же расширения при старте. Автоматический
старт расширения в `gui.sh` требует проверки при следующем запуске GUI.

## Остановка и повторный запуск

На хосте:

```bash
docker stop isaac-lab-base-vkr
docker start isaac-lab-base-vkr
```

`exit` завершает только оболочку, открытую через `enter`.
После перезагрузки хоста временный X11-файл может исчезнуть. Если обычный
`docker start` не может подключить его, повторите команду `container.py start`
с тем же дополнением и суффиксом, затем выполните `enter`.

Для обычной остановки используйте `docker stop`: в этой версии
`container.py stop` вызывает `docker compose down --volumes` и удаляет тома.

## Воспроизводимость

Сохраняйте код и настройки в Git, модели и результаты — в `research-data`.
Для каждого эксперимента заполните `configs/experiment.example.yaml`:
коммиты проекта и Isaac Lab, фактический образ, seed, данные и команду запуска.
ID образа работающего контейнера можно получить на хосте:

```bash
docker inspect --format '{{.Image}}' isaac-lab-base-vkr
```

Для переноса окружения сохраните проверенный образ в архив или реестр:
одно имя `:latest` не фиксирует его содержимое. Кэши Docker можно восстановить;
уникальные сцены, checkpoint и результаты должны иметь резервную копию.
