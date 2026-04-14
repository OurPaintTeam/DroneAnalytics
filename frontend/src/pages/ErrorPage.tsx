import {Link, useRouteError, isRouteErrorResponse} from "react-router-dom"

export default function ErrorPage() {
    const error = useRouteError()

    let message = "Unknown error"

    if (isRouteErrorResponse(error)) {
        message = `${error.status} ${error.statusText}`
    } else if (error instanceof Error) {
        message = error.message
    } else if (typeof error === "object" && error !== null) {
        const err = error as any
        message = err?.message || err?.error?.message || JSON.stringify(err)
    }

    return (
        <div className="flex h-screen items-center justify-center bg-gray-100">
            <div className="text-center">

                <h1 className="text-6xl font-bold text-red-500">
                    Error
                </h1>

                <h2 className="text-2xl mt-4 font-semibold">
                    Unexpected Application Error
                </h2>

                <pre className="mt-2 text-gray-600 whitespace-pre-wrap">
                    {message}
                </pre>

                <Link
                    to="/"
                    className="inline-block mt-6 px-6 py-3 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                    Go Home
                </Link>

            </div>
        </div>
    )
}