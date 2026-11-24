// What differs between the YouTube and the LinkedIn Accounts manager: the words on screen and the calls behind the buttons.
// The manager components take `kind` ("youtube" | "linkedin") and read everything from here, so both platforms look and behave the same.
import { connectAccount_, mgrAdd, mgrCheck, mgrDelete, mgrEdit, mgrList, mgrValues, setYtAccount, ytDisconnect } from "./api.js"
import { signInPopup } from "./liPopup.js"
import { xConnect, xDisconnect, xMgrAdd, xMgrCheck, xMgrDelete, xMgrEdit, xMgrList, xMgrValues, xSignInPopup } from "./xApi.js"
import { liConnect, liDisconnect, liMgrAdd, liMgrCheck, liMgrDelete, liMgrEdit, liMgrList, liMgrValues, liToken } from "./liApi.js"

export const KINDS = {
  youtube: {
    name: "YouTube", home: "/youtube", unit: "channel", appWord: "Google app", heroClass: "hero--yt", asking: "Google",
    title: "Accounts and channels",
    sub: "Give a Google client ID and secret, sign in, and post to that channel. Add as many accounts as you need, and see exactly what each one is missing.",
    panelSub: "Each account is one channel, signed in with its own Google login.",
    reuseNote: "Use this for a second channel, or a second Google login, on the same Google app. You sign in separately for each. All of them share that Google project's limits.",
    removeNote: "This removes the saved Google app and sign-in from this computer. Videos already on YouTube are not touched.",
    labelPlaceholder: "channel-owner@gmail.com", idPlaceholder: "123456789-abc.apps.googleusercontent.com", secretPlaceholder: "GOCSPX-...", notes: "google",
    redirectLabel: "Authorized redirect URIs", valuesTitle: "Values Google may ask for",
    list: mgrList, add: mgrAdd, edit: mgrEdit, remove: mgrDelete, check: mgrCheck, values: mgrValues,
    connect: (key, opts = {}) => connectAccount_(key, opts, "accounts"),
    disconnect: async (key) => { setYtAccount(key); await ytDisconnect() },
    studio: (key) => `/youtube/studio?account=${key}`,
  },
  linkedin: {
    name: "LinkedIn", home: "/linkedin", unit: "profile", appWord: "LinkedIn app", heroClass: "hero--li", asking: "LinkedIn",
    title: "Accounts and profiles",
    sub: "Give a LinkedIn app's client ID and secret, sign in, and post to that profile. Add as many accounts as you need, and see exactly what each one is missing.",
    panelSub: "Each account is one LinkedIn member, signed in with that person's own LinkedIn login.",
    reuseNote: "Use this for a second person on the same LinkedIn app. You sign in separately for each. All of them share that app's limits.",
    removeNote: "This removes the saved LinkedIn app and sign-in from this computer. Posts already on LinkedIn are not touched.",
    labelPlaceholder: "name@company.com", idPlaceholder: "78abcdefgh1234", secretPlaceholder: "WPL_AP1.xxxx.xxxx==", notes: "none",
    redirectLabel: "Authorized redirect URLs for your app", valuesTitle: "Value LinkedIn asks for",
    list: liMgrList, add: liMgrAdd, edit: liMgrEdit, remove: liMgrDelete, check: liMgrCheck, values: liMgrValues,
    connect: (key) => liConnect(key, "accounts"),
    popup: signInPopup,  // Connect opens LinkedIn in a popup window
    disconnect: (key) => liDisconnect(key),
    studio: null,
    // No redirect URL needed: a token made in the portal's token generator signs the account in.
    token: liToken, tokenLink: { label: "Open the token generator", url: "https://www.linkedin.com/developers/tools/oauth/token-generator" },
    tokenSteps: ["Open the token generator and pick your LinkedIn app.", "Tick openid, profile, email and w_member_social, press Request access token and allow it. If those are not listed, add the two products on the app's Products tab first.", "Copy the token and paste it here."],
  },
  x: {
    name: "X", article: "an", home: "/x", unit: "account", appWord: "X app", heroClass: "hero--x", asking: "X",
    title: "Accounts",
    sub: "Give an X app's OAuth 2.0 Client ID and Secret, sign in, and post to that account. Add as many accounts as you need, and see exactly what each one is missing.",
    panelSub: "Each account is one X account, signed in with its own X login.",
    reuseNote: "Use this for a second X account on the same X app. You sign in separately for each. All of them share that app's credits and limits.",
    removeNote: "This removes the saved X app and sign-in from this computer. Posts already on X are not touched.",
    labelPlaceholder: "@handle or email", idPlaceholder: "OAuth 2.0 Client ID", secretPlaceholder: "OAuth 2.0 Client Secret", notes: "none",
    redirectLabel: "Callback URI / Redirect URL", valuesTitle: "Value X asks for",
    list: xMgrList, add: xMgrAdd, edit: xMgrEdit, remove: xMgrDelete, check: xMgrCheck, values: xMgrValues,
    connect: (key) => xConnect(key, "accounts"),
    popup: xSignInPopup,  // Connect opens X in a popup window
    disconnect: (key) => xDisconnect(key),
    studio: null,
  },
}
