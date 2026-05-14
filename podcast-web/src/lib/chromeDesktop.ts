/**
 * Grabación en navegador está pensada solo para Chrome en escritorio.
 */
export function isChromeDesktop(): boolean {
  if (typeof navigator === "undefined") return false;

  const ud = (
    navigator as Navigator & {
      userAgentData?: { brands: { brand: string }[]; mobile: boolean };
    }
  ).userAgentData;

  if (ud) {
    if (ud.mobile) return false;
    return ud.brands.some((b) => b.brand === "Google Chrome");
  }

  const ua = navigator.userAgent;
  if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)) {
    return false;
  }
  const isEdge = /Edg\//.test(ua);
  const isOpera = /OPR\//.test(ua);
  const isBrave = /Brave/i.test(ua);
  const isGoogleChrome = /Chrome\//.test(ua) && !isEdge && !isOpera && !isBrave;
  return isGoogleChrome;
}
