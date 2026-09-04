export function hasPermission(permissions: string[] | undefined, code: string): boolean {
  return Boolean(permissions?.includes(code));
}
