/** Допустимые значения совпадают с Query limit у GET /log/* (ge=1, le=100). */
export const LOG_PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const

export const LOG_PAGE_DEFAULT = 10

export type LogPageSize = (typeof LOG_PAGE_SIZE_OPTIONS)[number]

export function buildLogListSearchParams(
    filterParams: URLSearchParams,
    page: number,
    limit: number
): URLSearchParams {
    const p = new URLSearchParams(filterParams)
    p.set("page", String(page))
    p.set("limit", String(limit))
    return p
}
