import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useLogout, fetchCurrentUser } from "../api/auth";

export function useAuth() {
  const navigate = useNavigate();
  const logoutMutation = useLogout();
  const queryClient = useQueryClient();

  const token = localStorage.getItem("access_token");
  const isAuthenticated = !!token;

  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["currentUser"],
    queryFn: fetchCurrentUser,
    enabled: isAuthenticated,
    retry: false,
  });

  const logout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: () => {
        // B16 fix: clear all cached query data on successful logout
        queryClient.clear();
        navigate("/login");
      },
      onError: () => {
        // Even on error, clear local tokens, cache, and redirect
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        queryClient.clear();
        navigate("/login");
      },
    });
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    logout,
  };
}
