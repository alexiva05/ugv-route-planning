# Контейнер ВКР

Рабочий контейнер проекта: `isaac-lab-ugv`. Старый контейнер
`isaac-lab-base` остаётся отдельным.

## Папки

- Код: `~/robotics/ugv-route-planning` → `/workspace/ugv-route-planning` (только чтение).
- Данные: `~/robotics/research-data` → `/workspace/research-data` (чтение и запись).
- Исходники IsaacLab подключены к контейнеру ВКР только для чтения.
- Результаты сохранять в `/workspace/research-data/runs/`.

## Повседневные команды

Войти от своего пользователя:

`docker exec -it --user "$(id -u):$(id -g)" --env HOME=/workspace/research-data --workdir /workspace/ugv-route-planning isaac-lab-ugv bash --noprofile --norc`

Остановить только контейнер ВКР: `docker stop isaac-lab-ugv`

Снова запустить его: `docker start isaac-lab-ugv`

После перезагрузки временный X11-файл может исчезнуть; тогда
`docker start` сообщит об отсутствующем пути. Не используйте для остановки
`IsaacLab/docker/container.py stop`: в этой версии он удаляет тома Docker.

Статус `starting` или `unhealthy` означает, что проверка Docker пока не
нашла `AppReady` в журнале Isaac Sim. При запущенной одной оболочке
это ожидаемо и не является результатом проверки самой симуляции.

## Первое создание контейнера

Нужны уже собранный локальный образ `isaac-lab-base`, соседние каталоги
`IsaacLab`, `ugv-route-planning`, `research-data` и действующий X11-файл.
Запуск выполняется из каталога `IsaacLab/docker`:

    cd "$HOME/robotics/IsaacLab/docker"
    xauth_path=$(awk -F= '/^__isaaclab_tmp_xauth/ {
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2
    }' .container.cfg)
    if [ -f "$xauth_path" ]; then
      export __ISAACLAB_TMP_XAUTH="$xauth_path"
      export __ISAACLAB_TMP_DIR="$(dirname "$xauth_path")"

      docker compose -p ugv-route-planning \
        -f docker-compose.yaml \
        -f ../../ugv-route-planning/docker/compose.override.yaml \
        -f x11.yaml \
        --profile base --env-file .env.base \
        up -d --no-build --no-deps --no-recreate --pull never isaac-lab-base
    else
      echo "X11-файл отсутствует; запуск отменён" >&2
    fi

`-p ugv-route-planning` выделяет собственные тома. Три файла `-f`
передаются по порядку: официальный compose, подключения ВКР, X11.
`--no-build --pull never` использует уже готовый образ. Если X11-файл
отсутствует, команда остановится до запуска Docker.
