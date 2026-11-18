/** Matrícula: duas letras maiúsculas (A-Z) e seis dígitos (0-9), ex.: KM482731. */
export const FORMATO_DA_MATRICULA = /^[A-Z]{2}[0-9]{6}$/;
export const TAMANHO_DA_MATRICULA = 8;

export function matriculaValida(valor: string): boolean {
  return FORMATO_DA_MATRICULA.test(valor);
}

/**
 * Ajuda a digitação: maiúsculas, sem espaços ou símbolos, no máximo 8 caracteres.
 * Não "corrige" o conteúdo: só facilita; a validação de verdade é do servidor.
 */
export function normalizarDigitacaoDaMatricula(valor: string): string {
  return valor
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, TAMANHO_DA_MATRICULA);
}
