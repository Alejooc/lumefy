import packageInfo from '../../package.json';

export const environment = {
  appVersion: packageInfo.version,
  production: true,
  // Production traffic goes through nginx so the browser uses its current origin.
  apiUrl: '/api/v1'
};
