# Fish Price service
This is web api for realtime fish price website.


## Installation

Clone the repository from GitLab:

```
git clone https://erathia.deepsea9.taipei/fish-price/fish-price-backend
```

Install dependencies for this project:

```
pipenv install
```

## Configuration

1. config/db.example.yaml

- host: db server ip
- port: db port
- user: db user
- password: db user password

```yaml
host : "host"
port : "27017"
user : "admin"
password : "password"
```

2. deploy.example.py

- bind: the arg can be "server_ip:port" or unix socket

```yaml
bind = 'unix:/tmp/fish-price.sock'

workers = 4
worker_class = 'gevent'

proc_name = 'fish-price.proc'
pidfile = '/tmp/fish-price.pid'
```

3. fish-price-backend.example.conf
- listen: api port
- server_name: api server ip or domain name
- proxy_pass: this arg should be the same as the bind arg at deploy.example.py
```conf
server {
    listen port;
    server_name server_name;
    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/fish-price.sock;
    }
}
```

## Deployment
1. After modifying config file, please rename them from xxx.example.oo to xxx.oo.

2. Move quota-backend.conf to /etc/nginx/conf.d
3. Reload nginx
```
sudo service nginx reload
```
4. Run
```
pipenv run gunicorn -c deploy.py app:APP
```

## Develop
Before start developing, you should install the dev environment and git hook. Git hook may run lint and test on every commit.

1. Install all dependencies for this project (including dev):
```
pipenv install --dev
```

2. Install git hook:

**If you are using windows, you should use git bash to run the following command.**

```
cp pre-commit .git/hooks
chmod +x .git/hooks/pre-commit
```

## Documentation

./config/fish-price.yml

http://192.168.100.233:8002/swagger-ui/

## Related
[fish-price-frontend](https://erathia.deepsea9.taipei/fish-price/fish-price-frontend) - a website repository that visualizes fish price

[fish-price-crawler](https://erathia.deepsea9.taipei/fish-price/fish-price-crawler) - a crawler repository that collects fish price data and upsert into our db