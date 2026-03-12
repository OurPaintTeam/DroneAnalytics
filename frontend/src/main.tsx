import {StrictMode} from 'react'
import {createRoot} from 'react-dom/client'
import {RouterProvider, Navigate, createBrowserRouter} from "react-router-dom"
import "./index.css"

import TopBar from "./components/TopBar.tsx"

import EventLog from "./pages/EventLogPage.tsx";
import SecurityLog from "./pages/SecurityLogPage.tsx";
import TelemetryLog from "./pages/TelemetryLogPage.tsx";
import LoginPage from "./pages/LoginPage.tsx";
import AboutPage from "./pages/AboutPage.tsx";
import CommandsPage from "./pages/CommandsPage.tsx";
import ErrorPage from "./pages/ErrorPage.tsx"

const router = createBrowserRouter([

    {
        path: "/login",
        element: <LoginPage/>,
        errorElement: <ErrorPage/>
    },

    {
        path: "/",
        element: <TopBar/>,
        errorElement: <ErrorPage/>,
        children: [
            {index: true, element: <Navigate to="/event" replace/>},
            {path: "event", element: <EventLog/>},
            {path: "safety", element: <SecurityLog/>},
            {path: "telemetry", element: <TelemetryLog/>},
            {path: "about", element: <AboutPage/>},
            {path: "commands", element: <CommandsPage/>},
        ],
    },
])

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <RouterProvider router={router}/>
    </StrictMode>
)
