from flask import Flask, request, render_template_string

app = Flask(__name__)

TEMPLATE = '''
<!doctype html>
<html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <title>Time to Study</title>
        <style>body{font-family:system-ui,Segoe UI,Roboto,Arial;margin:36px}</style>
    </head>
    <body>
        <h1>Take a Study Break</h1>
        <p>You tried to visit: <strong>{{original}}</strong></p>
        <p>This site is blocked. Please take a moment to study instead.</p>
        <p><a href="/">Back to home</a></p>
        <p>
            <button id="finishBtn">I finished studying</button>
        </p>
        <script>
            (function(){
                const params = new URLSearchParams(location.search);
                const orig = params.get('from') || '';
                document.getElementById('finishBtn').addEventListener('click', () => {
                    // call the special grant URL so the extension can pick it up and allow the original host temporarily
                    const grantUrl = '/grant?from=' + encodeURIComponent(orig);
                    // use fetch to call grant endpoint on this server; extension will see the request and set allowList
                    fetch(grantUrl).finally(() => {
                        // after granting, redirect to the original site (will be allowed briefly by the extension)
                        if (orig) {
                            const target = (orig.startsWith('http') ? orig : ('http://' + orig));
                            window.location.href = target;
                        }
                    });
                });
            })();
        </script>
    </body>
</html>
'''

@app.route('/study')
def study():
        original = request.args.get('from', '')
        return render_template_string(TEMPLATE, original=original)


@app.route('/grant')
def grant():
    from_host = request.args.get('from', '')
    return (f'granted:{from_host}', 200)

if __name__ == '__main__':
        app.run(host='127.0.0.1', port=5000)