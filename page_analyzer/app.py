import os
from dotenv import load_dotenv
import requests

from flask import (
    Flask,
    request,
    render_template,
    flash,
    get_flashed_messages,
    redirect,
    url_for,
    abort
)
from bs4 import BeautifulSoup

from page_analyzer import database, url as url_module


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.secret_key = "secret_key"


@app.route('/')
def main_page():
    return render_template(
        'index.html',
        input_url='',
        flash_messages=get_flashed_messages(with_categories=True)
    )


@app.route('/urls', methods=['POST'])
def add_url():
    url = url_module.normalize_url(request.form.get('url'))
    if url_module.is_url_correct(url):
        if database.is_url_recorded(url):
            flash('Страница уже существует', 'info')
        else:
            database.add_url(url)
            flash('Страница успешно добавлена', 'success')
        id = database.get_url_id(url)
        return redirect(url_for('url_page', id=id))
    else:
        flash('Некорректный URL', 'error')
        return render_template(
            'index.html',
            input_url=url,
            flash_messages=get_flashed_messages(with_categories=True)
        ), 422


@app.route('/urls')
def urls_list():
    return render_template(
        'urls.html',
        flash_messages=get_flashed_messages(with_categories=True),
        urls=database.get_urls_with_checks()
    )


@app.route('/urls/<id>')
def url_page(id):
    response = database.get_url_by_id(id)
    if not response:
        abort(404)
    id, url, created_at = response

    return render_template(
        'url.html',
        flash_messages=get_flashed_messages(with_categories=True),
        id=id,
        url=url,
        created_at=created_at,
        checks=database.get_checks(id)
    )


@app.route('/urls/<id>/checks', methods=['POST'])
def conduct_check(id):
    try:
        response = requests.get(database.get_url_by_id(id)[1])
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        description_tag = soup.find('meta',
                                    attrs={'name': 'description'})
        database.add_check(
            id,
            response.status_code,
            soup.title.string if soup.title else None,
            soup.h1.string if soup.h1 else None,
            description_tag['content'] if description_tag else None
        )
        flash('Страница успешно проверена', 'success')
    except Exception:
        flash('Произошла ошибка при проверке', 'error')

    return redirect(url_for('url_page', id=id))


@app.errorhandler(404)
def page_404(_):
    return render_template(
        '404.html',
        flash_messages=get_flashed_messages(with_categories=True)
    )
