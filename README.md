### Commands for GUnicorn

```
# equivalent to 'from hello import app'
$ gunicorn -w 4 'hello:app'

# equivalent to 'from hello import create_app; create_app()'
$ gunicorn -w 4 'hello:create_app()'

```
### GitHub Action Runner Execution

```
GH Action will start with running checkout and terraform setup.
```