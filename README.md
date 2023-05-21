## Install requirements

`pip install -r requirements.txt`

## Start server

`flask --app ./src/server/server.py run`

## Vue

```
cd src/server/vue
npm run dev			# start dev server
npm run build		# build files to be served by Flask
```

## OCR

add your openai key as os environment variable (OPENAI_API_KEY)

in server.py USE_GPU bool and USE_PYTESSERACT (don't)