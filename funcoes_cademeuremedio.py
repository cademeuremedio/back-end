import datetime
import os

import pandas as pd
import unidecode
from pymongo import MongoClient


def normaliza(termo):
    """  Descrição: Esta função retira acentos, caracteres especiais e deixa tudo em maiúsculas para facilitar a busca pelo termo
    """
    return (
        unidecode.unidecode(termo.upper()).replace(",", "").replace('.', '').replace(';', '').replace('  ',
                                                                                                      ' ').replace('"',
                                                                                                                   '').replace(
            '"', ''))


def lista_medicamentos_sus(termo):
    """  Descrição: Esta função busca pelo termo na lista de medicamentos do RENAME (/data/listaRENAME.csv), elaborada a partir do pdf
    disponível em http://portalms.saude.gov.br/assistencia-farmaceutica/medicamentos-rename, assim como pelos nomes comerciais,
     com base na lista disponibilizada no repositório github.com/aspto/base-de-dados-de-medicamentos .
     TODO: colocar essas listas no mongoDB
    """
    termo = normaliza(termo)
    dfl = dfListaRename[
        dfListaRename["remedio"].str.contains(termo)]

    if (dfl.empty):
        # encontra por nome comercial
        principios = busca_principio_por_nome_comercial(termo)
        for principio in principios:
            result = dfListaRename[dfListaRename["remedio"].str.contains(principio)]
            if not result.empty:
                result['comercial'] = busca_nome_comercial(termo)
                if dfl.empty:
                    dfl = result
                else:
                    dfl = pd.concat([dfl, result])
        if not dfl.empty:
            return dfl[['id', 'remedio', 'comercial']].head(10)
    else:
        return dfl[['id', 'remedio', 'comercial']].head(10)

    return pd.DataFrame({"ERROR": termo + ' não encontrado.'}, index=[0])


def busca_principio_por_nome_comercial(termo):
    dfl = dfListaProdutos[dfListaProdutos['PRODUTO'].str.contains(termo)]
    if (dfl.empty):
        return pd.DataFrame()
    else:
        return dfl['PRINCIPIO ATIVO']


def busca_nome_comercial(termo):
    """Busca o nome comercial de um principio. Deve estar em maiusculo"""
    try:
        return dfListaProdutos[dfListaProdutos['PRODUTO'].str.contains(termo)]['PRODUTO'].iloc[0]
    except:
        return pd.DataFrame()


def todos_remedios(termo):
    termo = normaliza(termo)
    dfl = dfListaProdutos[dfListaProdutos['PRINCIPIO ATIVO'].str.contains(termo)]
    if (dfl.empty):
        dfl = dfListaProdutos[dfListaProdutos['PRODUTO'].str.contains(termo)]
    return dfl.head(100)


def retira_nao_tem_no_sus(lista):
    for row in lista.iterrows():
        if not tem_no_sus(str(row[0])):
            print(str(row[0]))
            lista = lista.drop(row[0])
            # print('nao tem')
    return lista


def tem_no_sus(remedio):
    remedio = normaliza(remedio).split('0')[0]
    return not dfListaRename[dfListaRename["PRINCIPIO"].str.contains(remedio)].empty


def grava_falta_remedio_por_municipio(posto, remedio, municipio, ip):
    novo_item = {"cod_posto": posto,
                 "remedio_id": remedio,
                 "municipio": municipio}
    report = {"data": datetime.datetime.now(), "ip": ip}
    item = collection.find_one(novo_item)

    score = 1
    if item:
        score = 1 + score_simples(item["reports_negativos"])
        collection.update_one(item, {'$addToSet': {'reports_negativos': report},
                                     '$set': {'score_simples': score}})
        # collection.update_one(item,{'$push': report} )
    else:
        novo_item["reports_negativos"] = [report]
        novo_item["score_simples"] = score
        item = collection.insert_one(novo_item)

    # grava max_score_simples
    max_score_municipio = db.scores_municipios.find_one({"_id": municipio})
    if max_score_municipio:
        if max_score_municipio["score_simples"] < score:
            db.scores_municipios.update_one({"_id": municipio}, {'$set': {'score_simples': score}})
    else:
        db.scores_municipios.insert_one({"_id": municipio,
                                         'score_simples': score})

    return item


def score_123(posto, remedio, municipio):
    max_score_municipio = db.scores_municipios.find_one({"_id": municipio})
    if max_score_municipio:
        busca = {"cod_posto": posto,
                 "remedio_id": remedio,
                 "municipio": municipio}
        posto = collection.find_one(busca)

        if posto:
            score_normalizado = posto["score_simples"] / max_score_municipio["score_simples"]
            print(score_normalizado)
            if score_normalizado < 0.33:
                return 1
            if score_normalizado < 0.67:
                return 2
            return 3
    return 1


def score_simples(reports):
    score = 0
    # base para o decaimento exponencial: score += base ** (dataAtual - dataDenuncia[i])
    # ex.: dias  = 7    (uma semana)
    #      fator = 1/10
    # ou seja, o score de uma denúncia hoje, equivale ao de 10 denúncias há 7 dias
    fator = 1 / 10
    dias = 7
    base = fator ** (1 / dias)

    # qtde_denuncias = len(denuncias[(posto, remedio,,municipio)])

    for report in reports:
        # print (report["data"])
        dias = (datetime.datetime.now() - report["data"]).days
        # print(str(report["data"]) + " = " + str(dias))
        if dias <= 30:
            score += base ** dias
            print(score)

    return score


def ranking(qtde):
    """
        TODO: implementar """
    return ''


dfListaProdutos = pd.read_json('data/listaISO.json')
dfListaProdutos = dfListaProdutos[["PRINCIPIO ATIVO", "PRODUTO", "APRESENTACAO"]]

dfListaRename = pd.read_csv('data/listaRENAME.csv', names=["PRINCIPIO ATIVO", "COMPOSICAO", "COMPONENTE"])
dfListaRename['PRINCIPIO'] = dfListaRename["PRINCIPIO ATIVO"].apply(normaliza)
dfListaRename['remedio'] = dfListaRename['PRINCIPIO'] + dfListaRename["COMPOSICAO"].apply(normaliza) + dfListaRename[
    "COMPONENTE"].apply(normaliza)
dfListaRename['id'] = dfListaRename.index
dfListaRename.rename(index=str, columns={"COMPONENTE": "APRESENTACAO", "COMPOSICAO": "PRODUTO"})
dfListaRename['comercial'] = ""

# reclamacoes = dict()
# max_score = dict()
# max_score["municipio"] = 0


# Inicializa MongoDB

mongo_url = os.getenv('MONGODB_CADEMEUREMEDIO', 'mongodb://localhost:27017')
conn = MongoClient(mongo_url)
db = conn[os.getenv('DBNAME_CADEMEUREMEDIO', 'cademeuremedio')]

collection = db.reports


# TODO: Guardar valores no BD: listas de remedios consolida (relacionando rename e nomes comerciais), assim como os reports dos usuários
# TODO: Arrumar RuntimeWarning: numpy.dtype size changed, may indicate binary incompatibility. Expected 96, got 88
# TODO: Trocar o Flask por um WGSI ("Do not use the development server in a production environment.  Use a production WSGI server instead.')
