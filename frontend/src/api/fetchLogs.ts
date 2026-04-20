import {BACKEND_URL} from "../config"
import {ApiError, ApiErrorCode} from "../components/notify.ts";

/**
 * GET логов с query; ответ проверяется как JSON-массив.
 * Токен только в заголовке, не в URL.
 */
export async function fetchLogJsonArray(
    path: string,
    searchParams: URLSearchParams
): Promise<unknown[]> {

    const access = localStorage.getItem("access_token")

    if (!access) {
        throw new ApiError(ApiErrorCode.NO_TOKEN)
    }

    await checkBackend()

    const q = searchParams.toString()
    const url = `${BACKEND_URL}${path}${q ? `?${q}` : ""}`

    let res: Response

    try {
        res = await fetch(url, {
            headers: { Authorization: `Bearer ${access}` },
        })
    } catch {
        throw new ApiError(ApiErrorCode.NETWORK_ERROR)
    }

    if (!res.ok) {
        switch (res.status) {
            case 401:
                throw new ApiError(ApiErrorCode.UNAUTHORIZED)
            case 403:
                throw new ApiError(ApiErrorCode.FORBIDDEN)
            case 404:
                throw new ApiError(ApiErrorCode.NOT_FOUND)
            case 500:
                throw new ApiError(ApiErrorCode.SERVER_ERROR)
            default:
                throw new ApiError(ApiErrorCode.SERVER_ERROR)
        }
    }

    const data = await res.json()

    if (!Array.isArray(data)) {
        throw new ApiError(ApiErrorCode.INVALID_RESPONSE)
    }

    return data
}

export async function checkBackend(): Promise<void> {
    try {
        const res = await fetch(`${BACKEND_URL}/`, {
            method: "GET",
            cache: "no-store"
        })

        if (!res.ok) {
            throw new ApiError(ApiErrorCode.BACKEND_DOWN)
        }
    } catch {
        throw new ApiError(ApiErrorCode.NETWORK_ERROR)
    }
}