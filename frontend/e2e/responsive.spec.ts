import { test, expect } from '@playwright/test'

const PUBLIC_PAGES = ['/', '/meciuri', '/grupe', '/bracket', '/clasament']

for (const width of [320, 375]) {
  test(`fără scroll orizontal pe paginile publice la ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    for (const path of PUBLIC_PAGES) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')
      // Lasă layout-ul să se așeze (countdown-uri, fonturi).
      await page.waitForTimeout(300)
      const overflow = await page.evaluate(() => {
        const de = document.documentElement
        return { scrollW: de.scrollWidth, clientW: de.clientWidth }
      })
      expect(
        overflow.scrollW,
        `${path} @ ${width}px: scrollWidth ${overflow.scrollW} > clientWidth ${overflow.clientW}`,
      ).toBeLessThanOrEqual(overflow.clientW)
    }
  })
}
