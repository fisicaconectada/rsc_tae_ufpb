# Monitor RSC-TAE UFPB

Painel que acompanha, de hora em hora, o andamento das solicitações de RSC/TAE em
tramitação na UFPB, com base na [Consulta Pública oficial](https://rsctae.ufpb.br/portal).

O painel é o arquivo `docs/index.html`, gerado automaticamente pelo script
`update_rsc_data.py` a partir da API pública da UFPB. O histórico fica em
`docs/rsc_history.csv`, e uma cópia resumida (para o gráfico) fica embutida
dentro do próprio `docs/index.html`.

## Como funciona a atualização automática

O workflow em `.github/workflows/update.yml` roda no GitHub Actions:
de hora em hora, das 7h às 20h (horário de Brasília), de segunda a sexta-feira.
A cada execução ele roda `update_rsc_data.py`, que busca os números atuais na
API oficial e faz commit + push do `docs/index.html` e `docs/rsc_history.csv`
atualizados.

## Passo a passo para ativar (fazer uma única vez)

1. **Enviar estes arquivos para o repositório**, na raiz dele:
   ```bash
   git add .
   git commit -m "Adiciona monitor RSC-TAE automático"
   git push
   ```

2. **Permitir que o Actions faça commit/push:**
   Vá em `Settings` → `Actions` → `General` → seção **Workflow permissions**
   → selecione **"Read and write permissions"** → **Save**.
   (Sem isso, o workflow roda mas falha ao tentar publicar a atualização.)

3. **Ativar o GitHub Pages:**
   Vá em `Settings` → `Pages` → em **Build and deployment / Source**,
   escolha **"Deploy from a branch"** → Branch: **main**, pasta: **/docs** → **Save**.
   Depois de alguns minutos o painel fica disponível em:
   `https://fisicaconectada.github.io/rsc_tae_ufpb/`

4. **Rodar a primeira atualização manualmente** (não precisa esperar a próxima hora cheia):
   Vá na aba `Actions` do repositório → clique no workflow **"Atualizar Monitor RSC-TAE"**
   → botão **"Run workflow"** → **Run workflow**.
   Isso gera o primeiro `docs/index.html` com dados reais.

## Como colocar no site (Google Sites)

No editor do Google Sites (fisicaconectada.com.br):

1. Abra a página onde quer o painel.
2. No menu lateral direito, clique em **Inserir** → **Inserir** (bloco genérico) → **Por URL**.
3. Cole a URL do GitHub Pages: `https://fisicaconectada.github.io/rsc_tae_ufpb/`
4. Ajuste o tamanho do bloco (o painel é responsivo e se adapta à largura disponível,
   inclusive em celular).
5. Publique a página.

Alternativa mais simples: em vez de embutir, você também pode só colocar um
**botão/link** apontando para essa mesma URL, se preferir que o painel abra
em página própria.

## Rodar manualmente (opcional, para testar localmente)

```bash
python3 update_rsc_data.py
```

Gera/atualiza `docs/index.html` e `docs/rsc_history.csv` com os dados mais
recentes da API pública da UFPB.
