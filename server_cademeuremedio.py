import os

import requests
from flask import Flask
from flask import request
from flask_cors import CORS, cross_origin

import funcoes_cademeuremedio as f

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.route("/")
@cross_origin()
def raiz():
    return "#CadêMeuRemêdio"


@app.route("/meuip")
@cross_origin()
def meuip():
    return "#CadêMeuRemêdio   IP: " + request.headers['X-Forwarded-For']


@app.route('/lista')
@app.route('/lista/<termo>')
@cross_origin()
def lista_medicamentos_sus(termo):
    if not termo:
        return 'uso correto: /lista/<termo>'
    else:
        return f.lista_medicamentos_sus(termo).to_json(orient='records')


@app.route('/denuncia/<cod_posto>/<cod_medicamento>/<cod_municipio>')
@app.route('/reporta_falta/<cod_posto>/<cod_medicamento>/<cod_municipio>')
@cross_origin()
def reporta_falta(cod_posto, cod_medicamento, cod_municipio, id_usr=''):
    if not cod_posto:
        return 'uso correto: /reporta_falta/<cod_posto>/<cod_medicamento>/<cod_municipio>  ou <br> /reporta_falta/<cod_posto>/<cod_medicamento>/<cod_municipio>/<id_usr>'
    return str(f.grava_falta_remedio_por_municipio(cod_posto, cod_medicamento, cod_municipio,
                                                   request.headers['X-Forwarded-For']))


# esse "proxy" é necessário porque a API do TCU não está em https.
@app.route('/estabelecimentos/latitude/<latitude>/longitude/<longitude>')
@app.route('/estabelecimentos/latitude/<latitude>/longitude/<longitude>/raio/<raio>')
@cross_origin()
def estabelecimentos(latitude, longitude, raio=50):
    r = requests.get(
        'http://mobile-aceite.tcu.gov.br/mapa-da-saude/rest/estabelecimentos/latitude/' + latitude + '/longitude/' + longitude + '/raio/' + raio + '?categoria=POSTO%20DE%20SA%C3%9ADE')
    # r = requests.get('http://mobile-aceite.tcu.gov.br/mapa-da-saude/rest/estabelecimentos/latitude/-27.5926371/longitude/-48.5576378/raio/50?categoria=POSTO%20DE%20SA%C3%9ADE')
    return r.text


@app.route('/score/<cod_posto>/<cod_medicamento>/<cod_municipio>')
@cross_origin()
def score(cod_posto, cod_medicamento, cod_municipio):
    return '{"resultado":"' + str(f.score_123(cod_posto, cod_medicamento, cod_municipio)) + '"}'


@app.route('/ranking')
@app.route('/ranking/<qtde>')
@app.route('/ranking/<cidade>/<qtde>')
@cross_origin()
def ranking(qtde=10, cidade=0):
    return f.ranking(qtde)


@app.route('/todos_remedios/<termo>')
@cross_origin()
def todos_remedios(termo):
    return f.todos_remedios(termo).to_json(orient='records')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7777))
    app.run(host='0.0.0.0', port=port, debug=False)
