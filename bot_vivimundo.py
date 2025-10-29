# bot_vivimundo.py
import os
import json
import pickle
import random
import requests
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import google.generativeai as genai

# ==================== CONFIGURAÇÕES ====================
BLOG_ID = '4602463746754711403'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SCOPES = ['https://www.googleapis.com/auth/blogger']

# Temas do blog
TEMAS = ['Esportes', 'Games', 'Entretenimento', 'Tecnologia']

# ==================== AUTENTICAÇÃO BLOGGER ====================
def autenticar_blogger():
    """Autentica com a API do Blogger"""
    creds = None
    
    # Carrega credenciais do token se existir
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Se não há credenciais válidas
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Carrega credentials.json do ambiente
            creds_data = os.environ.get('BLOGGER_CREDENTIALS')
            if creds_data:
                creds_dict = json.loads(creds_data)
                flow = InstalledAppFlow.from_client_config(
                    creds_dict, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                raise Exception("BLOGGER_CREDENTIALS não encontrado!")
        
        # Salva token para próxima execução
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('blogger', 'v3', credentials=creds)

# ==================== BUSCAR NOTÍCIAS ====================
def buscar_noticias(tema, quantidade=3):
    """Busca notícias recentes sobre um tema usando Google News RSS"""
    print(f"🔍 Buscando notícias sobre: {tema}")
    
    queries = {
        'Esportes': 'esportes+futebol+brasil OR basquete OR volei',
        'Games': 'games+jogos+videogame OR playstation OR xbox OR nintendo',
        'Entretenimento': 'entretenimento+cinema+series OR filmes OR netflix',
        'Tecnologia': 'tecnologia+tech OR smartphones OR inteligencia+artificial'
    }
    
    query = queries.get(tema, tema)
    
    try:
        # Usa Google News RSS
        url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            # Parse simples do RSS
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            noticias = []
            for item in root.findall('.//item')[:quantidade]:
                titulo = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                descricao = item.find('description').text if item.find('description') is not None else ''
                
                noticias.append({
                    'titulo': titulo,
                    'link': link,
                    'descricao': descricao
                })
            
            print(f"✓ Encontradas {len(noticias)} notícias sobre {tema}")
            return noticias
    except Exception as e:
        print(f"✗ Erro ao buscar notícias: {e}")
    
    return []

# ==================== GERAR ARTIGO COM GEMINI ====================
def gerar_artigo(tema, noticias):
    """Gera um artigo original baseado nas notícias"""
    print(f"✍️  Gerando artigo sobre {tema}...")
    
    # Configura Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    
    # Monta o contexto com as notícias
    contexto = f"Tema: {tema}\n\nNotícias recentes:\n"
    for i, noticia in enumerate(noticias, 1):
        contexto += f"\n{i}. {noticia['titulo']}\n"
        if noticia['descricao']:
            contexto += f"   {noticia['descricao'][:200]}...\n"
    
    # Prompt para o Gemini
    prompt = f"""Você é um redator do blog "Vivimundo" (vivimund0.blogspot.com).

{contexto}

Escreva um artigo ORIGINAL e INFORMATIVO sobre este tema, usando as notícias acima como referência (mas NÃO copie texto delas).

REQUISITOS:
- Título chamativo e criativo
- Introdução envolvente
- 3-4 parágrafos de desenvolvimento
- Tom descontraído mas informativo
- Entre 400-600 palavras
- Use HTML básico: <h2>, <p>, <strong>, <em>
- NÃO mencione as fontes originais
- Seja original e criativo

Formato de resposta:
TÍTULO: [seu título aqui]
CONTEÚDO:
[seu artigo em HTML aqui]"""
    
    try:
        response = model.generate_content(prompt)
        texto = response.text
        
        # Extrai título e conteúdo
        if 'TÍTULO:' in texto and 'CONTEÚDO:' in texto:
            partes = texto.split('CONTEÚDO:')
            titulo = partes[0].replace('TÍTULO:', '').strip()
            conteudo = partes[1].strip()
        else:
            # Fallback se formato não for seguido
            linhas = texto.split('\n')
            titulo = linhas[0].strip('#').strip()
            conteudo = '\n'.join(linhas[1:])
        
        print(f"✓ Artigo gerado: {titulo[:50]}...")
        return titulo, conteudo
        
    except Exception as e:
        print(f"✗ Erro ao gerar artigo: {e}")
        return None, None

# ==================== PUBLICAR NO BLOGGER ====================
def publicar_post(service, titulo, conteudo, labels):
    """Publica um post no Blogger"""
    print(f"📤 Publicando: {titulo[:50]}...")
    
    post = {
        'kind': 'blogger#post',
        'title': titulo,
        'content': conteudo,
        'labels': labels
    }
    
    try:
        resultado = service.posts().insert(
            blogId=BLOG_ID,
            body=post
        ).execute()
        
        print(f"✓ Post publicado com sucesso!")
        print(f"  URL: {resultado.get('url', 'N/A')}")
        return True
        
    except Exception as e:
        print(f"✗ Erro ao publicar: {e}")
        return False

# ==================== FUNÇÃO PRINCIPAL ====================
def main():
    """Executa o bot"""
    print("=" * 60)
    print("🤖 BOT VIVIMUNDO - Gerador Automático de Conteúdo")
    print("=" * 60)
    print(f"⏰ Execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Verifica API Key
    if not GEMINI_API_KEY:
        print("✗ ERRO: GEMINI_API_KEY não configurada!")
        return
    
    # Autentica no Blogger
    try:
        service = autenticar_blogger()
        print("✓ Autenticado no Blogger")
    except Exception as e:
        print(f"✗ Erro na autenticação: {e}")
        return
    
    # Gera 1 post por execução (GitHub Actions vai rodar várias vezes)
    tema = random.choice(TEMAS)
    print(f"\n📰 Tema escolhido: {tema}")
    
    # Busca notícias
    noticias = buscar_noticias(tema, quantidade=3)
    
    if not noticias:
        print("✗ Nenhuma notícia encontrada. Tentando outro tema...")
        tema = random.choice([t for t in TEMAS if t != tema])
        noticias = buscar_noticias(tema, quantidade=3)
    
    if noticias:
        # Gera artigo
        titulo, conteudo = gerar_artigo(tema, noticias)
        
        if titulo and conteudo:
            # Publica
            labels = [tema.lower(), 'vivimundo', 'notícias']
            sucesso = publicar_post(service, titulo, conteudo, labels)
            
            if sucesso:
                print("\n" + "=" * 60)
                print("✅ BOT EXECUTADO COM SUCESSO!")
                print("=" * 60)
            else:
                print("\n⚠️  Post gerado mas não publicado")
        else:
            print("\n✗ Falha ao gerar artigo")
    else:
        print("\n✗ Não foi possível buscar notícias")

if __name__ == "__main__":
    main()
