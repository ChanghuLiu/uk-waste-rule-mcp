FROM python:3.12-slim

WORKDIR /app
COPY . /app

# x402 is deliberately installed at image-build time rather than imported by
# local/offline tests. Keep the version aligned with the existing RegEvidenceHub
# x402 v2 vertical services.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir '.[mcp]' 'x402[evm]==2.21.0' \
    && python -c "import mcp, x402; print('WASTE_RUNTIME_IMPORT=PASS')"

ENV WASTE_PAYMENT_ENFORCED=0
ENV HOST=0.0.0.0

CMD ["uk-waste-rule-mcp-http"]
