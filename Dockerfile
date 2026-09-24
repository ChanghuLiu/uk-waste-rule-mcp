FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Keep x402 aligned with the RegEvidenceHub vertical services and run the
# exact compile/test gate inside the image that Railway will deploy.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir '.[mcp,dev]' 'x402[evm]==2.21.0' \
    && python -c "import httpx, mcp, x402; print('WASTE_RUNTIME_IMPORT=PASS')" \
    && python -m compileall -q src \
    && pytest -q

ENV WASTE_PAYMENT_ENFORCED=0
ENV HOST=0.0.0.0

CMD ["uk-waste-rule-mcp-http"]
