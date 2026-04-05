import {BACKEND_URL} from "../config"

/**
 * GET логов с query; ответ проверяется как JSON-массив.
 * Токен только в заголовке, не в URL.
 */
export async function fetchLogJsonArray(path: string, searchParams: URLSearchParams): Promise<unknown[]> {
    const access = localStorage.getItem("access_token")
    if (!access) return []
    const q = searchParams.toString()
    const url = `${BACKEND_URL}${path}${q ? `?${q}` : ""}`
    const res = await fetch(url, {
        headers: {Authorization: `Bearer ${access}`},
    })
    if (!res.ok) return []
    const data: unknown = await res.json()
    return Array.isArray(data) ? data : []
}
