from flask import Flask, request, jsonify, send_file
from fpdf import FPDF
import os
from datetime import datetime
import io
import math
import base64

app = Flask(__name__, static_folder='../public', static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('index.html')

# --- LOGIN DOS USUÁRIOS ---
USUARIOS = {
    "lucasspv": "admin123", 
    "nutribom": "vendas2026"
}

# --- IMAGEM LOGO EM STRING BASE64 (À PROVA DE ERRO DE CAMINHO) ---
LOGO_BASE64_PADRAO = (
    "iVBORw0KGgoAAAANSUhEUgAAAGQAAAAyCAMAAACg138FAAAABGdBTUEAALGPC/xhBQAAACBjSFJN"
    "AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAX1BMVEUAAADy8vL////y8vLy"
    "8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy"
    "8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vL6F3YBAAAAHnRSTlMAESIzM0RVZnd4iIqRlpuen6Kj"
    "qKusra+wsbS2t7u8vQp9SgAAAAFiS0dEAIgFHUgAAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElN"
    "QfUHCxYVEx96P68AAAAnSURBVFjD7cExAQAAAMKg9U9tDB8gAAAAAAAAAAAAAAAAAAAAADgshgAB"
    "4K1m0QAAAABJRU5ErkJggg=="
)

class PDFWeb(FPDF):
    def __init__(self, emitente, cliente, obs, desconto):
        super().__init__()
        self.emitente = emitente
        self.cliente = cliente
        self.obs = obs
        self.desconto = desconto

    def header(self):
        # Usa exclusivamente o Base64 na Vercel para eliminar erros de caminhos de arquivos locais
        try:
            img_data = base64.b64decode(LOGO_BASE64_PADRAO)
            img_io = io.BytesIO(img_data)
            self.image(img_io, 10, 8, 38, format="PNG")
        except Exception as e:
            print(f"Erro ao carregar imagem em memória: {e}")
        
        self.set_font("Helvetica", 'B', 15)
        self.set_text_color(40, 40, 40)
        self.set_xy(100, 8)
        self.cell(100, 8, self.emitente['nome'].upper(), 0, 1, 'R')
        
        self.set_font("Helvetica", '', 9)
        self.set_text_color(80, 80, 80)
        self.set_x(100)
        self.cell(100, 4, f"CNPJ: {self.emitente['cnpj']}", 0, 1, 'R')
        self.set_x(100)
        self.cell(100, 4, f"Contato: {self.emitente['tel']}", 0, 1, 'R')
        
        self.ln(18)
        self.set_draw_color(200, 200, 200)
        self.line(10, 38, 200, 38)
        
        self.set_y(42)
        self.set_font("Helvetica", 'B', 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 5, "INFORMAÇÕES DO CLIENTE", ln=1)
        
        self.set_font("Helvetica", 'B', 11)
        self.set_text_color(40, 40, 40)
        self.cell(0, 6, self.cliente['nome'].upper(), ln=1)
        
        self.set_font("Helvetica", '', 9)
        # Exibe "CNPJ/CPF" ao invés de "Documento"
        self.cell(100, 5, f"CNPJ/CPF: {self.cliente['cnpj']}", 0, 0)
        self.cell(0, 5, f"Telefone: {self.cliente['tel']}", 0, 1, 'R')
        self.cell(0, 5, f"Data da Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1)
        self.ln(3)

    def draw_table_header(self):
        self.set_fill_color(240, 240, 240)
        self.set_text_color(60, 60, 60)
        self.set_font("Helvetica", 'B', 8)
        self.cell(20, 10, "CODIGO", 0, 0, 'C', True)
        self.cell(85, 10, "DESCRICAO DO PRODUTO", 0, 0, 'L', True)
        self.cell(15, 10, "QTD", 0, 0, 'C', True)
        self.cell(15, 10, "UN", 0, 0, 'C', True)
        self.cell(25, 10, "P. UNIT", 0, 0, 'R', True)
        self.cell(30, 10, "TOTAL", 0, 1, 'R', True)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", 'I', 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, f"Nutribom Alimentos - Pagina {self.page_no()}/{{nb}}", 0, 0, 'C')

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.json
    usuario = dados.get('usuario')
    senha = dados.get('senha')
    if USUARIOS.get(usuario) == senha:
        return jsonify({"sucesso": True})
    return jsonify({"sucesso": False, "mensagem": "Usuário ou senha incorretos."}), 401

@app.route('/api/gerar_pdf', methods=['POST'])
def gerar_pdf():
    dados = request.json
    emitente = dados.get('emitente')
    cliente = dados.get('cliente')
    itens = dados.get('itens', [])
    desconto = float(str(dados.get('desconto', 0)).replace(',', '.'))
    obs = dados.get('obs', '')

    pdf = PDFWeb(emitente, cliente, obs, desconto)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.draw_table_header()
    
    pdf.set_font("Helvetica", '', 9)
    t_bruto = 0
    for idx, i in enumerate(itens):
        pdf.set_fill_color(255) if idx % 2 == 0 else pdf.set_fill_color(252)
        
        # Lê os campos tratando letras maiúsculas e minúsculas com segurança para evitar vazios
        item_id = str(i.get('id', i.get('ID', '')))
        item_nome = str(i.get('nome', i.get('NOME', '')))
        item_un = str(i.get('un', i.get('UN', '')))
        
        try:
            item_qtd = float(str(i.get('qtd', i.get('QTD', 1))).replace(',', '.'))
        except:
            item_qtd = 1.0
            
        try:
            item_preco = float(str(i.get('preco', i.get('PRECO', 0))).replace(',', '.'))
        except:
            item_preco = 0.0
            
        try:
            item_total = float(str(i.get('total', i.get('TOTAL', 0))).replace(',', '.'))
        except:
            item_total = item_qtd * item_preco

        h, text = 6, item_nome
        rh = math.ceil(pdf.get_string_width(text) / 83) * h
        cy = pdf.get_y()
        if cy + rh > 270: 
            pdf.add_page()
            pdf.draw_table_header()
            
        pdf.cell(20, rh, item_id, 0, 0, 'C', True)
        pdf.multi_cell(85, h, text, 0, 'L', True)
        pdf.set_xy(pdf.get_x() + 105, cy)
        
        # Renderiza os dados numéricos e as strings
        pdf.cell(15, rh, f"{item_qtd:.2f}", 0, 0, 'C', True)
        pdf.cell(15, rh, item_un, 0, 0, 'C', True)
        pdf.cell(25, rh, f"R$ {item_preco:.2f}", 0, 0, 'R', True)
        pdf.cell(30, rh, f"R$ {item_total:.2f}", 0, 1, 'R', True)
        
        t_bruto += item_total

    pdf.ln(5)
    pdf.set_x(130)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 8, "Subtotal:", 0, 0, 'R')
    pdf.cell(30, 8, f"R$ {t_bruto:.2f}", 0, 1, 'R')
    
    dv = t_bruto * (desconto / 100)
    if dv > 0:
        pdf.set_x(130)
        pdf.cell(40, 8, f"Desconto ({desconto}%):", 0, 0, 'R')
        pdf.cell(30, 8, f"- R$ {dv:.2f}", 0, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_fill_color(26, 42, 58)
    pdf.set_text_color(255)
    pdf.cell(40, 10, "TOTAL FINAL:", 0, 0, 'R', True)
    pdf.cell(30, 10, f"R$ {t_bruto - dv:.2f}", 0, 1, 'R', True)
    
    pdf.ln(10)
    pdf.set_text_color(40)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "OBSERVACOES:", ln=1)
    pdf.set_font("Helvetica", '', 10)
    pdf.multi_cell(0, 6, obs if obs else "Nenhuma.")
    
    # fpdf2 gera bytes em formato direto na memória
    pdf_out = io.BytesIO(pdf.output())
    pdf_out.seek(0)
    
    return send_file(
        pdf_out,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Orcamento_{cliente['nome']}.pdf"
    )

if __name__ == '__main__':
    app.run(debug=True)