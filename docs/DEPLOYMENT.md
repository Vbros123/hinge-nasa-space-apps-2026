# Reproduce and deploy HINGE

## Frontend

Run `npm ci`, `npm test`, `npm run lint`, and `npm run build`. Serve `dist/` on a static HTTPS host or run `npm run preview` locally. The app uses static JSON under `/science/v1/`. Map background tiles come from OpenStreetMap.

For Vercel, link this repository to a Vite project. Use `npm ci` as the install command, `npm run build` as the build command, and `dist` as the output directory. No environment variables are required. A configured Git connection needs access to the private repository. For target validation, open the app, confirm the default science mode and test a rotation comparison after switching its historical window and parameter set.

## Science reproducibility

The [scientific backend](../science-backend/README.md) documents source-only tests, pinned replay dependencies, how to obtain the original environmental artifact from the team, and the exact regeneration and checksum workflow. The Python code is part of this repository. The cached environmental bundle is distributed separately. The Vercel build uses the committed browser assets and does not need Python or the external archive.
