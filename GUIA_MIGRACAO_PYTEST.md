# Guia de Resolução: Problemas com Pytest após Migração Poetry → uv

## 🔍 Diagnóstico Executado

### Comando executado:
```bash
uv sync --extra dev
uv pip install -e .
uv run pytest -v
```

### ⚠️ Problema Identificado:

**Erro crítico:** O comando `uv pip install -e .` **NÃO é necessário** e pode causar problemas com uv.

Com uv, quando você tem `[tool.uv] package = true` no `pyproject.toml`, o comando `uv sync` **JÁ instala o pacote em modo editável automaticamente**.

## ✅ Solução Correta (Simplificada)

### Etapa 1: Sincronizar ambiente (isso faz tudo)

Execute no diretório raiz do projeto:
```bash
uv sync --extra dev
```

**Ou para instalar todos os extras de uma vez:**
```bash
uv sync --all-extras
```

### Etapa 2: Executar os testes

```bash
uv run pytest -v
```

**Pronto!** Não é necessário nenhum comando adicional.

## 📋 Explicação Técnica Corrigida

### Diferença crucial: uv vs pip tradicional

Com **uv**, a configuração `[tool.uv] package = true` instrui o uv a:
1. Detectar que este é um pacote Python (não apenas uma coleção de scripts)
2. Automaticamente instalar o pacote em modo editável durante `uv sync`
3. Gerenciar tudo através do `uv.lock`

### O que acontece internamente:

```bash
uv sync --extra dev
```

Realiza automaticamente:
- ✅ Cria/atualiza o ambiente virtual
- ✅ Instala todas as dependências do `[project.dependencies]`
- ✅ Instala dependências de `[project.optional-dependencies.dev]`
- ✅ **Instala o pacote `bizdays` em modo editável**
- ✅ Atualiza o `uv.lock`

## 🔧 Comandos de Verificação

### 1. Verificar se o pacote está instalado corretamente:
```bash
uv run python -c "import bizdays; print(f'bizdays {bizdays.__version__} importado com sucesso!')"
```

**Saída esperada:**
```
bizdays 1.0.16 importado com sucesso!
```

### 2. Verificar pytest está disponível:
```bash
uv run pytest --version
```

### 3. Listar pacotes instalados:
```bash
uv pip list
```

Procure por:
- `bizdays` (deve aparecer)
- `pytest` (deve aparecer)
- `pandas-market-calendars` (dependência)
- `pandas` (dependência)

### 4. Executar testes com mais detalhes:
```bash
uv run pytest -vv
```

## 🆚 Comparação Atualizada: Poetry vs uv

| Ação | Poetry | uv |
|------|--------|-----|
| **Instalar projeto completo** | `poetry install` | `uv sync` |
| **Instalar com deps dev** | `poetry install` | `uv sync --extra dev` |
| **Instalar todos extras** | `poetry install --all-extras` | `uv sync --all-extras` |
| **Modo editável** | Automático | Automático (com `package = true`) |
| **Executar testes** | `poetry run pytest` | `uv run pytest` |
| **Adicionar dependência** | `poetry add pkg` | `uv add pkg` |

## 📝 Setup Inicial do Projeto (Novo Clone)

Se você clonou o repositório ou está configurando pela primeira vez:

```bash
# Opção 1: Apenas deps de desenvolvimento
uv sync --extra dev

# Opção 2: Todos os extras (dev + docs)
uv sync --all-extras

# Executar testes
uv run pytest -v
```

## ⚠️ Problemas Comuns e Soluções

### Problema 1: "ModuleNotFoundError: No module named 'bizdays'"

**Causa:** Ambiente não sincronizado ou `package = true` faltando.

**Solução:**
```bash
# Verifique o pyproject.toml tem [tool.uv] package = true
uv sync --extra dev
```

### Problema 2: "pytest: command not found"

**Causa:** Dependências de dev não instaladas.

**Solução:**
```bash
uv sync --extra dev
# Não use apenas 'uv sync' sem o --extra dev
```

### Problema 3: Testes falham por dependências faltando

**Causa:** Algumas dependências podem estar só em extras.

**Solução:**
```bash
uv sync --all-extras
```

### Problema 4: Cache desatualizado

**Causa:** uv.lock ou cache do pytest desatualizado.

**Solução:**
```bash
# Limpar e reinstalar
rm -rf .venv uv.lock
uv sync --extra dev
uv run pytest --cache-clear -v
```

## 🎯 Comandos Essenciais - Cheat Sheet

```bash
# Setup inicial
uv sync --all-extras

# Executar todos os testes
uv run pytest

# Executar com verbosidade
uv run pytest -v

# Executar com cobertura
uv run pytest --cov=bizdays --cov-report=term-missing

# Executar teste específico
uv run pytest tests/test_arquivo.py::test_funcao -v

# Executar testes que falham primeiro
uv run pytest --failed-first

# Modo watch (requer pytest-watch)
uv run ptw

# Adicionar nova dependência
uv add nome-do-pacote

# Adicionar dependência de dev
uv add --dev nome-do-pacote
```

## 📂 Estrutura de Arquivos Esperada

```
python-bizdays/
├── bizdays/              # Código fonte
│   ├── __init__.py      # Define __version__
│   ├── calendario.py
│   └── ...
├── tests/                # Testes
│   ├── __init__.py      # Pode ser vazio ou inexistente
│   ├── test_*.py
│   └── ...
├── pyproject.toml        # Configuração do projeto
├── uv.lock              # Lock file (gerado por uv sync)
├── .venv/               # Ambiente virtual (gerado automaticamente)
├── ANBIMA.cal           # Arquivos de calendário
├── B3.cal
├── Actual.cal
└── README.md
```

## 🔍 Troubleshooting Avançado

### Verificar configuração do pytest no pyproject.toml

Adicione se não existir:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v"
```

### Verificar se bizdays/__init__.py existe e está correto

Deve conter pelo menos:
```python
__version__ = "1.0.16"
```

### Executar em modo debug

```bash
uv run python -v -c "import bizdays"
```

Isso mostra todos os imports e ajuda a identificar problemas.

## ✅ Checklist Final

Antes de executar os testes, verifique:

- [ ] `pyproject.toml` contém `[tool.uv] package = true`
- [ ] Executou `uv sync --extra dev` (ou `--all-extras`)
- [ ] Arquivo `bizdays/__init__.py` existe
- [ ] Pasta `tests/` contém arquivos `test_*.py`
- [ ] **NÃO** executou `uv pip install -e .` (não é necessário!)

## 🎉 Comando Final - Solução Completa

**Execute isso e seus testes devem funcionar:**

```bash
uv sync --all-extras && uv run pytest -v
```

---

**Status:** ✅ Solução refinada - Use apenas `uv sync`, NÃO use `uv pip install -e .`

**Lição aprendida:** O uv gerencia o modo editável automaticamente quando `package = true` está configurado. Comandos `pip` tradicionais são desnecessários e podem causar confusão.
