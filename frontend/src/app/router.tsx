import { Navigate, createBrowserRouter } from "react-router-dom"

import { AuthGuard } from "@/features/auth/auth-guard"
import { AppLayout } from "@/layouts/app-layout"
import { AlertsPage } from "@/pages/alerts-page"
import { DashboardPage } from "@/pages/dashboard-page"
import { ItemDetailPage } from "@/pages/item-detail-page"
import { ItemFormPage } from "@/pages/item-form-page"
import { ItemsListPage } from "@/pages/items-list-page"
import { ItemsPage } from "@/pages/items-page"
import { InventoryPage } from "@/pages/inventory-page"
import { LoginPage } from "@/pages/login-page"
import { NotFoundPage } from "@/pages/not-found-page"
import { PatientDetailPage } from "@/pages/patient-detail-page"
import { PatientFormPage } from "@/pages/patient-form-page"
import { PatientsListPage } from "@/pages/patients-list-page"
import { PatientsPage } from "@/pages/patients-page"
import { PrescriptionFormPage } from "@/pages/prescription-form-page"
import { PrescriptionsListPage } from "@/pages/prescriptions-list-page"
import { PrescriptionsPage } from "@/pages/prescriptions-page"
import { UnitFormPage } from "@/pages/unit-form-page"
import { UnitsListPage } from "@/pages/units-list-page"
import { UnitsPage } from "@/pages/units-page"

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <AuthGuard />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <Navigate replace to="/dashboard" />,
          },
          {
            path: "alerts",
            element: <AlertsPage />,
          },
          {
            path: "dashboard",
            element: <DashboardPage />,
          },
          {
            path: "patients",
            element: <PatientsPage />,
            children: [
              {
                index: true,
                element: <PatientsListPage />,
              },
              {
                path: "new",
                element: <PatientFormPage />,
              },
              {
                path: ":patientId",
                element: <PatientDetailPage />,
              },
              {
                path: ":patientId/edit",
                element: <PatientFormPage />,
              },
            ],
          },
          {
            path: "inventory",
            element: <InventoryPage />,
          },
          {
            path: "items",
            element: <ItemsPage />,
            children: [
              {
                index: true,
                element: <ItemsListPage />,
              },
              {
                path: "new",
                element: <ItemFormPage />,
              },
              {
                path: ":itemId",
                element: <ItemDetailPage />,
              },
              {
                path: ":itemId/edit",
                element: <ItemFormPage />,
              },
            ],
          },
          {
            path: "prescriptions",
            element: <PrescriptionsPage />,
            children: [
              {
                index: true,
                element: <PrescriptionsListPage />,
              },
              {
                path: "new",
                element: <PrescriptionFormPage />,
              },
              {
                path: ":prescriptionId/edit",
                element: <PrescriptionFormPage />,
              },
            ],
          },
          {
            path: "units",
            element: <UnitsPage />,
            children: [
              {
                index: true,
                element: <UnitsListPage />,
              },
              {
                path: "new",
                element: <UnitFormPage />,
              },
              {
                path: ":unitId/edit",
                element: <UnitFormPage />,
              },
            ],
          },
          {
            path: "*",
            element: <NotFoundPage />,
          },
        ],
      },
    ],
  },
])
