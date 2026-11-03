import {
  signInWithGoogle,
  signInEmailPassword,
  signUpEmailPassword,
  signOutUser,
  currentUser,
  auth,
  isFirebaseConfigured,
} from "../firebase";

export const authService = {
  signInWithGoogle,
  signInWithEmail: signInEmailPassword,
  signUpWithEmail: signUpEmailPassword,
  signOut: signOutUser,
  getCurrentUser: currentUser,
  auth,
  isConfigured: isFirebaseConfigured,
};

export default authService;

