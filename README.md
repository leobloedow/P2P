# Projeto P2P de Sincronização de Arquivos (UDP + Python)

Este projeto implementa um sistema simples de **sincronização de arquivos** entre múltiplos peers usando **UDP** em Python.

## Passos de uso em Docker

1. **Iniciar containers**  
   Abra dois ou mais containers:
   ```bash
   docker container run -it python:3.12 bash
   ```
   Dentro de cada container:
   ```bash
   apt update
   apt install net-tools
   ```

2. **Preparar diretório**  
   Em cada container, crie um diretório (ex.: `/peer`) com:
   - `peer.py` (código deste repositório)
   - `ips.txt` (lista de peers)
   - `tmp/` (pasta sincronizada)
     
   ```bash
   mkdir -p /peer/tmp
   cd /peer
   ```

3. **Configurar IPs**  
   Verifique o IP de cada container com `ifconfig`.
   No `ips.txt` de todos os peers, liste os IPs e portas, **um por linha**, por exemplo:
   ```
   172.17.0.2:5001
   172.17.0.3:5001
   ```
   Todos os peers devem ter o mesmo conteúdo em `ips.txt`.

4. **Executar peer**  
   Em cada container, a partir do diretório onde estão `peer.py`, `ips.txt` e `tmp/`:
   ```bash
   python peer.py
   ```

5. **Testar sincronização**  
   Criar, editar ou remover arquivos em `tmp/` de um container deve refletir nos outros.

## Padrões
- Porta padrão: `5001`
- Pasta padrão: `tmp/` no mesmo diretório do `peer.py`
- Arquivo de peers: `ips.txt` no mesmo diretório.
