# Backend

Backend FastAPI com PostgreSQL local para desenvolvimento.

## Antes de começar

- Use terminal normal, sem modo administrador.
- No Windows, prefira clonar o projeto em uma pasta curta, por exemplo:
  - `C:\ProjetoExtensao`
- No repositorio clonado, o backend correto fica em:
  - `C:\ProjetoExtensao\backend`

## Subida rapida

```powershell
cd C:\ProjetoExtensao\backend
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\dev_postgres.ps1 start
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## O que o script do PostgreSQL faz

- usa runtime fora do repositorio
- faz validacao preventiva para caminho longo
- tenta fallback automatico em `C:\CasaAssistencialRuntime`
- extrai so o necessario para o backend local

## Verificacao

- health: `http://127.0.0.1:8000/health`
- swagger: `http://127.0.0.1:8000/docs`

## Login padrao

- e-mail: `admin@casa.local`
- senha: `admin123456`
