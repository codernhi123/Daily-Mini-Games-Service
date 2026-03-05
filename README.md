# This is a full-stack group project that has been migrated from an existing code base granted by Professor Kasra Jamshidi @SFU.

Our team adapted from a janky web service that handles user accounts into use, turning it into a fully working daily game play system.

The application was a class project and has been permitted to become a fully licensed personal project.


## Step-by-step instructions on how to launch the code base locally.

1. Make a `.env` file containing the following, and DO NOT check it into git:

```
POSTGRES_HOST=db
POSTGRES_USER=Group14
POSTGRES_PASSWORD=Group14
POSTGRES_DB=Group14
ADMIN_PASSWORD=sharedpassword123
STORAGE_SECRET=Check the most recent project release
JWT_PRIVATE_KEY=Check the most recent project release
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

2. Launch the application by running:

```
$ docker compose watch
```

The service is now running on `localhost:8000/`.
You can visit `localhost:8000/admin`, `localhost:8000/docs`, and `localhost:8000/redoc` in your browser.

If you edit any of the files in this repo, the server restarts to reflect your changes.


3. You can follow the logs by running:
```
$ docker compose logs -f [service_name]
```
`service_name` is optional, if you only want to see logs for a given service (one of `web` or `db`).

* You may run into a ResourceExhausted: failed to copy files: userspace copy failed: write /app/.venv/bin/ruff: no space left on device.

```
$ docker system prune --volumes
```


* You can run tests as follows:
```
$ docker compose exec web pytest
```

Use the following links for local deployment:
for admin page - http://localhost:8000/profile/admin
for redoc page - http://localhost:8000/redoc
for docs page - http://localhost:8000/docs
for game leaderboard page - http://localhost:8000/
for game frontend user creation page - http://localhost:8000/profile/create
for game frontend user friend creation page - http://localhost:8000/profile/friends
for game home page - http://localhost:5173/

Use the following links for render deployment:
for admin page - https://user-service-lxv0.onrender.com/profile/admin
for redoc page - https://user-service-lxv0.onrender.com/redoc
for docs page - https://user-service-lxv0.onrender.com/docs
for game leaderboard page - https://user-service-lxv0.onrender.com/
for game frontend user creation page - https://user-service-lxv0.onrender.com/profile/create
for game frontend user friend creation page - https://user-service-lxv0.onrender.com/profile/friends
for game home page - https://game-frontend-mwlw.onrender.com/

Please use the following commands for testing analytics: 
curl http://localhost:8000/v2/events/
curl http://localhost:8000/v2/analytics/streaks
curl http://localhost:8000/v2/analytics
