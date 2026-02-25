import packageJson from '../../package.json';

export const environment = {
  appVersion: packageJson.version,
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'
};
