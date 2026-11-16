import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./routes/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import DoctorDashboard from "./pages/DoctorDashboard";
import PatientPortalPage from "./pages/PatientPortalPage";
import PatientTimelinePage from "./pages/PatientTimelinePage";
import ClinicalReportPreviewPage from "./pages/ClinicalReportPreviewPage";
import DoctorReportsPage from "./pages/DoctorReportsPage";
import PatientReportsPage from "./pages/PatientReportsPage";
import PatientReportDetailPage from "./pages/PatientReportDetailPage";
import UnsupportedRolePage from "./pages/UnsupportedRolePage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/doctor"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <DoctorDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/doctor/patients/:patientId"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <PatientTimelinePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/doctor/reports"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <DoctorReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/doctor/reports/:reportId"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <ClinicalReportPreviewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient"
            element={
              <ProtectedRoute allowedRoles={["PATIENT"]}>
                <PatientPortalPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient/reports"
            element={
              <ProtectedRoute allowedRoles={["PATIENT"]}>
                <PatientReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient/reports/:reportId"
            element={
              <ProtectedRoute allowedRoles={["PATIENT"]}>
                <PatientReportDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/unsupported-role"
            element={
              <ProtectedRoute allowedRoles={["NURSE", "ADMIN_STAFF", "SYSTEM_ADMIN"]}>
                <UnsupportedRolePage />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
