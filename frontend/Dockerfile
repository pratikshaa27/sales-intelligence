FROM node:20-alpine AS base
WORKDIR /app
COPY package.json ./
RUN npm install

FROM base AS development
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM base AS build
# NEXT_PUBLIC_* vars are inlined into the client bundle at build time, not read at runtime —
# this must be a build ARG, not just a compose `environment:` entry on the running container.
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
COPY . .
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "server.js"]
