import { LoadingState, ErrorState } from './storeUtils';

export function getLoadingCompat(loading: LoadingState): boolean {
  return loading.isLoading;
}

export function getErrorCompat(error: ErrorState): string | null {
  return error.error;
}

export function getErrorMessage(error: ErrorState): string {
  if (!error.error) return '';
  
  const recoveryText = error.recoveryActions.length > 0 
    ? ` Try: ${error.recoveryActions.join(', ')}`
    : '';
    
  return `${error.error}${recoveryText}`;
}