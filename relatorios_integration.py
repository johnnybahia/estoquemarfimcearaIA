#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integração de Relatórios com Flask - Marfim Estoque Ceará
Autor: Johnny
Data: 2026-02-13

Endpoints para geração de relatórios inteligentes.

INSTRUÇÃO: Adicione ao app_final.py com:
    from relatorios_integration import register_relatorios_routes
    register_relatorios_routes(app)
"""

from flask import jsonify, request, send_file
from relatorios import gerenciador_relatorios, ConfigRelatorios
import logging
import io

logger = logging.getLogger(__name__)


def register_relatorios_routes(app):
    """
    Registra endpoints de relatórios na aplicação Flask
    """

    @app.route('/api/relatorios/completo', methods=['GET'])
    def gerar_relatorio_completo():
        """
        📊 Gera relatório completo do estoque

        GET /api/relatorios/completo?periodo=mes

        Query Params:
        - periodo: hoje | semana | mes | trimestre | personalizado
        - data_inicio: DD/MM/YYYY (se personalizado)
        - data_fim: DD/MM/YYYY (se personalizado)

        Response:
        {
          "periodo": "mes",
          "data_geracao": "13/02/2026 10:30",
          "total_itens": 150,
          "total_grupos": 12,
          "saldo_geral": 45230.0,
          "total_movimentacoes": 850,
          "total_entradas": 12000.0,
          "total_saidas": 9500.0,
          "itens_zerados": 5,
          "itens_sem_movimento": 18,
          "curva_abc": { "A": [...], "B": [...], "C": [...] },
          "resumo_grupos": [...],
          "top_movimentados": [...],
          "itens_parados": [...],
          "grafico_abc": {...},
          "grafico_grupos": {...},
          "grafico_movimentacoes": {...}
        }
        """
        try:
            periodo = request.args.get('periodo', 'mes')
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')

            periodos_validos = ['hoje', 'semana', 'mes', 'trimestre', 'personalizado']
            if periodo not in periodos_validos:
                return jsonify({
                    'error': f'Período inválido. Use: {", ".join(periodos_validos)}'
                }), 400

            if periodo == 'personalizado' and not (data_inicio and data_fim):
                return jsonify({
                    'error': 'Para período personalizado, informe data_inicio e data_fim (DD/MM/YYYY)'
                }), 400

            relatorio = gerenciador_relatorios.gerar_relatorio_completo(
                periodo=periodo,
                data_inicio=data_inicio,
                data_fim=data_fim
            )

            return jsonify(relatorio.to_dict()), 200

        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/relatorios/curva-abc', methods=['GET'])
    def obter_curva_abc():
        """
        📊 Obtém Curva ABC do estoque

        GET /api/relatorios/curva-abc?classe=A

        Query Params:
        - classe: A | B | C | todas (padrão: todas)

        Response:
        {
          "curva_abc": {
            "A": [
              {
                "item": "AMARELO 1234",
                "grupo": "FIOS",
                "volume_total": 5000.0,
                "percentual_volume": 25.0,
                "percentual_acumulado": 25.0,
                "classe": "A"
              }
            ],
            "B": [...],
            "C": [...]
          },
          "resumo": {
            "total_itens": 150,
            "classe_a": 10,
            "classe_b": 30,
            "classe_c": 110
          }
        }
        """
        try:
            classe_filtro = request.args.get('classe', 'todas').upper()

            curva = gerenciador_relatorios.calcular_curva_abc()

            if classe_filtro in ('A', 'B', 'C'):
                resultado = {classe_filtro: [i.to_dict() for i in curva.get(classe_filtro, [])]}
            else:
                resultado = {
                    k: [i.to_dict() for i in v]
                    for k, v in curva.items()
                }

            return jsonify({
                'curva_abc': resultado,
                'resumo': {
                    'total_itens': sum(len(v) for v in curva.values()),
                    'classe_a': len(curva.get('A', [])),
                    'classe_b': len(curva.get('B', [])),
                    'classe_c': len(curva.get('C', []))
                }
            }), 200

        except Exception as e:
            logger.error(f"Erro ao calcular curva ABC: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/relatorios/grupos', methods=['GET'])
    def obter_resumo_grupos():
        """
        📦 Obtém resumo por grupos

        GET /api/relatorios/grupos

        Response:
        {
          "grupos": [
            {
              "grupo": "FIOS",
              "total_itens": 25,
              "saldo_total": 8500.0,
              "total_movimentacoes": 200,
              "total_entradas": 5000.0,
              "total_saidas": 4000.0,
              "itens_zerados": 2,
              "itens_criticos": 5,
              "classe_predominante": "A"
            }
          ],
          "total": 12
        }
        """
        try:
            resumos = gerenciador_relatorios.calcular_resumo_grupos()

            return jsonify({
                'grupos': [r.to_dict() for r in resumos],
                'total': len(resumos)
            }), 200

        except Exception as e:
            logger.error(f"Erro ao obter grupos: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/relatorios/itens-parados', methods=['GET'])
    def obter_itens_parados():
        """
        ⏸️ Obtém itens sem movimentação

        GET /api/relatorios/itens-parados?dias=30

        Query Params:
        - dias: int (padrão: 30) - dias sem movimento para considerar parado

        Response:
        {
          "itens_parados": [
            {
              "item": "AZUL 5678",
              "grupo": "FIOS",
              "saldo": 150.0,
              "dias_sem_movimento": 45,
              "ultima_movimentacao": "01/01/2026",
              "status": "critico"
            }
          ],
          "total": 18,
          "dias_referencia": 30
        }
        """
        try:
            dias = request.args.get('dias', ConfigRelatorios.DIAS_SEM_MOVIMENTO_PARADO, type=int)

            parados = gerenciador_relatorios.obter_itens_parados(dias)

            return jsonify({
                'itens_parados': parados,
                'total': len(parados),
                'dias_referencia': dias
            }), 200

        except Exception as e:
            logger.error(f"Erro ao obter parados: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/relatorios/exportar/excel', methods=['GET'])
    def exportar_excel():
        """
        📥 Exporta relatório em Excel (.xlsx)

        GET /api/relatorios/exportar/excel?periodo=mes

        Query Params:
        - periodo: hoje | semana | mes | trimestre (padrão: mes)
        - data_inicio, data_fim: se personalizado

        Response: arquivo .xlsx para download
        """
        try:
            periodo = request.args.get('periodo', 'mes')
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')

            relatorio = gerenciador_relatorios.gerar_relatorio_completo(
                periodo=periodo,
                data_inicio=data_inicio,
                data_fim=data_fim
            )

            excel_bytes = gerenciador_relatorios.exportar_excel(relatorio)

            nome_arquivo = f"relatorio_marfim_{periodo}_{relatorio.data_geracao[:10].replace('/', '-')}.xlsx"

            return send_file(
                io.BytesIO(excel_bytes),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nome_arquivo
            )

        except ImportError:
            return jsonify({
                'error': 'openpyxl não instalado',
                'instrucao': 'Execute: pip install openpyxl'
            }), 500
        except Exception as e:
            logger.error(f"Erro ao exportar Excel: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/relatorios/exportar/pdf', methods=['GET'])
    def exportar_pdf():
        """
        📄 Exporta relatório em PDF

        GET /api/relatorios/exportar/pdf?periodo=mes

        Response: arquivo .pdf para download
        """
        try:
            periodo = request.args.get('periodo', 'mes')
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')

            relatorio = gerenciador_relatorios.gerar_relatorio_completo(
                periodo=periodo,
                data_inicio=data_inicio,
                data_fim=data_fim
            )

            pdf_bytes = gerenciador_relatorios.exportar_pdf(relatorio)

            nome_arquivo = f"relatorio_marfim_{periodo}_{relatorio.data_geracao[:10].replace('/', '-')}.pdf"

            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=nome_arquivo
            )

        except ImportError:
            return jsonify({
                'error': 'fpdf2 não instalado',
                'instrucao': 'Execute: pip install fpdf2'
            }), 500
        except Exception as e:
            logger.error(f"Erro ao exportar PDF: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/relatorios/graficos', methods=['GET'])
    def obter_graficos():
        """
        📈 Obtém dados de gráficos (Chart.js)

        GET /api/relatorios/graficos?periodo=mes

        Response:
        {
          "grafico_abc": {
            "type": "doughnut",
            "labels": ["Classe A", "Classe B", "Classe C"],
            "data": [10, 30, 110],
            "colors": ["#4CAF50", "#FF9800", "#F44336"]
          },
          "grafico_grupos": {
            "type": "bar",
            "labels": ["FIOS", "TECIDOS", ...],
            "datasets": [...]
          },
          "grafico_movimentacoes": {
            "type": "line",
            "labels": ["13/01", "14/01", ...],
            "datasets": [...]
          }
        }
        """
        try:
            periodo = request.args.get('periodo', 'mes')

            relatorio = gerenciador_relatorios.gerar_relatorio_completo(periodo=periodo)

            return jsonify({
                'grafico_abc': relatorio.grafico_abc,
                'grafico_grupos': relatorio.grafico_grupos,
                'grafico_movimentacoes': relatorio.grafico_movimentacoes
            }), 200

        except Exception as e:
            logger.error(f"Erro ao obter gráficos: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/relatorios/configuracoes', methods=['GET'])
    def obter_configuracoes():
        """
        ⚙️ Configurações dos relatórios

        GET /api/relatorios/configuracoes
        """
        try:
            return jsonify({
                'limite_classe_a': ConfigRelatorios.LIMITE_CLASSE_A,
                'limite_classe_b': ConfigRelatorios.LIMITE_CLASSE_B,
                'dias_sem_movimento_parado': ConfigRelatorios.DIAS_SEM_MOVIMENTO_PARADO,
                'top_n_movimentados': ConfigRelatorios.TOP_N_MOVIMENTADOS
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    logger.info("✅ Endpoints de relatórios registrados")


if __name__ == '__main__':
    print("📊 Endpoints de relatórios para Flask")
    print("✅ Use register_relatorios_routes(app) em app_final.py")
    print("")
    print("Endpoints:")
    print("  - GET /api/relatorios/completo")
    print("  - GET /api/relatorios/curva-abc")
    print("  - GET /api/relatorios/grupos")
    print("  - GET /api/relatorios/itens-parados")
    print("  - GET /api/relatorios/exportar/excel")
    print("  - GET /api/relatorios/exportar/pdf")
    print("  - GET /api/relatorios/graficos")
    print("  - GET /api/relatorios/configuracoes")
