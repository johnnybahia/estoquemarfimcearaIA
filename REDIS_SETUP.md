# 🚀 Instalação e Configuração do Redis - Sistema Marfim

> **Guia completo** para instalar e configurar o Redis no sistema de cache multinível

---

## 📋 O QUE É REDIS?

Redis (Remote Dictionary Server) é um banco de dados em memória ultra-rápido usado para cache.

**Benefícios:**
- ⚡ Velocidade extrema (<1ms de resposta)
- 🔄 Persistência opcional
- 📊 Estruturas de dados avançadas
- 🌐 Suporte distribuído

---

## 💻 INSTALAÇÃO

### **Linux (Ubuntu/Debian)**

```bash
# Atualiza repositórios
sudo apt update

# Instala Redis
sudo apt install redis-server -y

# Verifica instalação
redis-cli --version

# Inicia o serviço
sudo systemctl start redis-server

# Habilita auto-start
sudo systemctl enable redis-server

# Verifica status
sudo systemctl status redis-server
```

### **Mac OS**

```bash
# Usando Homebrew
brew install redis

# Inicia o serviço
brew services start redis

# Verifica instalação
redis-cli ping
# Deve retornar: PONG
```

### **Windows**

**Opção 1: WSL (Recomendado)**
```bash
# Instala WSL se ainda não tiver
wsl --install

# Dentro do WSL, segue passos do Linux acima
```

**Opção 2: Docker (Mais fácil)**
```bash
# Baixa e roda Redis em container
docker run -d -p 6379:6379 --name marfim-redis redis:latest

# Verifica
docker ps
```

**Opção 3: Redis para Windows (Não oficial)**
- Download: https://github.com/microsoftarchive/redis/releases
- Descompacte e execute `redis-server.exe`

---

## ⚙️ CONFIGURAÇÃO

### **1. Configuração Básica (Desenvolvimento)**

```bash
# Edita configuração (opcional)
sudo nano /etc/redis/redis.conf

# Configurações importantes:
# bind 127.0.0.1        # Apenas localhost (seguro)
# port 6379             # Porta padrão
# maxmemory 256mb       # Limite de memória (ajuste conforme necessário)
# maxmemory-policy allkeys-lru  # Remove keys antigas quando cheio
```

### **2. Configuração para Produção**

```bash
# /etc/redis/redis.conf

# Segurança
bind 127.0.0.1
protected-mode yes
requirepass SUA_SENHA_SEGURA_AQUI

# Performance
maxmemory 1gb
maxmemory-policy allkeys-lru

# Persistência (opcional - mantém dados após restart)
save 900 1
save 300 10
save 60 10000

# Logs
loglevel notice
logfile /var/log/redis/redis-server.log
```

### **3. Reinicia Redis após mudanças**

```bash
sudo systemctl restart redis-server
```

---

## 🔌 CONFIGURAÇÃO NO PROJETO

### **1. Variável de Ambiente**

Crie arquivo `.env` na raiz do projeto:

```bash
# .env
GROQ_API_KEY=gsk_sua_chave_aqui
REDIS_URL=redis://localhost:6379
```

Se Redis tiver senha:
```bash
REDIS_URL=redis://:sua_senha@localhost:6379
```

### **2. Instala Dependências Python**

```bash
pip install -r requirements.txt
```

Ou manualmente:
```bash
pip install redis>=5.0.0
```

### **3. Testa Conexão**

```python
# test_redis.py
from cache_config import cache_marfim

# Testa conexão
health = cache_marfim.health_check()
print(health)

# Deve mostrar:
# {'redis': {'available': True, 'status': 'ok'}, ...}
```

Ou via terminal:
```bash
python -c "from cache_config import cache_marfim; print(cache_marfim.health_check())"
```

---

## 🧪 TESTES

### **1. Teste Manual (Redis CLI)**

```bash
# Conecta ao Redis
redis-cli

# Testa set/get
127.0.0.1:6379> SET teste "Hello Redis"
OK
127.0.0.1:6379> GET teste
"Hello Redis"
127.0.0.1:6379> DEL teste
(integer) 1
127.0.0.1:6379> EXIT
```

### **2. Teste com o Sistema Marfim**

```bash
# Roda teste de performance
python test_performance.py

# Verifica estatísticas de cache
python -c "from cache_config import obter_estatisticas_cache; import json; print(json.dumps(obter_estatisticas_cache(), indent=2))"
```

### **3. Teste via API (se Flask estiver rodando)**

```bash
# Health check
curl http://localhost:5000/api/cache/health

# Estatísticas
curl http://localhost:5000/api/cache/stats
```

---

## 🔧 COMANDOS ÚTEIS

### **Redis CLI Básico**

```bash
# Conectar
redis-cli

# Listar todas as chaves
KEYS *

# Listar chaves do projeto Marfim
KEYS marfim:*

# Ver valor de uma chave
GET marfim:indice_completo

# Deletar uma chave
DEL marfim:indice_completo

# Deletar todas as chaves do projeto
KEYS marfim:* | xargs redis-cli DEL

# Limpar TODO o Redis (cuidado!)
FLUSHALL

# Informações do servidor
INFO

# Monitorar comandos em tempo real
MONITOR
```

### **Gerenciamento do Serviço**

```bash
# Linux
sudo systemctl status redis-server   # Ver status
sudo systemctl start redis-server    # Iniciar
sudo systemctl stop redis-server     # Parar
sudo systemctl restart redis-server  # Reiniciar
sudo systemctl enable redis-server   # Auto-start

# Mac
brew services status redis
brew services start redis
brew services stop redis
brew services restart redis

# Docker
docker start marfim-redis    # Iniciar
docker stop marfim-redis     # Parar
docker restart marfim-redis  # Reiniciar
docker logs marfim-redis     # Ver logs
```

---

## 🚨 TROUBLESHOOTING

### **Problema 1: Redis não inicia**

```bash
# Verifica logs
sudo tail -f /var/log/redis/redis-server.log

# Verifica se porta 6379 está em uso
sudo lsof -i :6379

# Mata processo se necessário
sudo kill -9 <PID>
```

### **Problema 2: Conexão recusada**

```bash
# Verifica se está rodando
sudo systemctl status redis-server

# Verifica bind address
grep ^bind /etc/redis/redis.conf

# Deve ser: bind 127.0.0.1
```

### **Problema 3: Python não conecta**

```python
# Testa conexão direta
import redis
r = redis.Redis(host='localhost', port=6379)
r.ping()  # Deve retornar True
```

Se der erro:
```bash
# Instala/reinstala biblioteca
pip uninstall redis
pip install redis>=5.0.0
```

### **Problema 4: Redis fica sem memória**

```bash
# Ver uso de memória
redis-cli INFO memory

# Limpa cache
redis-cli FLUSHDB

# Aumenta limite (edit /etc/redis/redis.conf)
maxmemory 2gb
```

---

## 🎯 MODO FALLBACK (SEM REDIS)

**O sistema funciona NORMALMENTE sem Redis!**

Se Redis não estiver disponível:
- ✅ Cache em memória (LRU) será usado automaticamente
- ✅ Todas as funcionalidades continuam funcionando
- ⚠️ Cache não é compartilhado entre processos
- ⚠️ Cache é perdido ao reiniciar a aplicação

**Logs típicos sem Redis:**
```
⚠️ Redis não disponível: Connection refused
💡 Cache funcionará apenas em memória (LRU)
✅ CacheMarfim inicializado - Redis: False
```

---

## 📊 MONITORAMENTO

### **1. Monitor de Performance**

```bash
# Estatísticas em tempo real
redis-cli --stat

# Info completo
redis-cli INFO
```

### **2. Via API do Sistema**

```python
# Em app_final.py
from cache_config import obter_estatisticas_cache

@app.route('/api/cache/monitor')
def monitor_cache():
    stats = obter_estatisticas_cache()
    return jsonify(stats)
```

Acesse: `http://localhost:5000/api/cache/monitor`

---

## 🔐 SEGURANÇA (PRODUÇÃO)

### **1. Configurar Senha**

```bash
# /etc/redis/redis.conf
requirepass SuaSenhaForteAqui123!
```

```bash
# .env
REDIS_URL=redis://:SuaSenhaForteAqui123!@localhost:6379
```

### **2. Firewall**

```bash
# Permite apenas localhost
sudo ufw deny 6379
sudo ufw allow from 127.0.0.1 to any port 6379
```

### **3. Bind apenas localhost**

```bash
# /etc/redis/redis.conf
bind 127.0.0.1
protected-mode yes
```

---

## ✅ CHECKLIST DE INSTALAÇÃO

- [ ] Redis instalado e rodando
- [ ] Teste `redis-cli ping` retorna `PONG`
- [ ] Variável `REDIS_URL` configurada em `.env`
- [ ] Dependência `redis>=5.0.0` instalada
- [ ] Teste Python: `cache_marfim.health_check()` retorna `ok`
- [ ] Script `test_performance.py` executado com sucesso
- [ ] Estatísticas de cache mostram hits de Redis

---

## 📚 RECURSOS ADICIONAIS

- **Documentação Oficial:** https://redis.io/documentation
- **Redis Python:** https://redis-py.readthedocs.io/
- **Redis Commander (GUI):** `npm install -g redis-commander`
- **RedisInsight (GUI Oficial):** https://redis.com/redis-enterprise/redis-insight/

---

## 🆘 SUPORTE

**Se tiver problemas:**

1. ✅ Verifica se Redis está rodando: `sudo systemctl status redis-server`
2. ✅ Verifica logs: `sudo tail -f /var/log/redis/redis-server.log`
3. ✅ Testa conexão: `redis-cli ping`
4. ✅ Verifica health: `python -c "from cache_config import cache_marfim; print(cache_marfim.health_check())"`
5. ✅ Se tudo falhar: Sistema funciona sem Redis (modo fallback)

---

**💡 Lembre-se:** O sistema foi projetado para funcionar com ou sem Redis. Redis é apenas uma otimização!

✅ **Instalação concluída? Execute:** `python test_performance.py` para ver os ganhos! 🚀
