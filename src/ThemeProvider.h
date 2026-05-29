#pragma once
#include <QObject>
#include <QString>

class ThemeProvider : public QObject {
    Q_OBJECT

    Q_PROPERTY(QString theme READ theme WRITE setTheme NOTIFY themeChanged)

    // Backgrounds
    Q_PROPERTY(QString navBg          READ navBg          NOTIFY themeChanged)
    Q_PROPERTY(QString baseBg         READ baseBg         NOTIFY themeChanged)
    Q_PROPERTY(QString surfaceBg      READ surfaceBg      NOTIFY themeChanged)
    Q_PROPERTY(QString inputBg        READ inputBg        NOTIFY themeChanged)
    Q_PROPERTY(QString titleBg        READ titleBg        NOTIFY themeChanged)
    Q_PROPERTY(QString windowBg       READ windowBg       NOTIFY themeChanged)
    Q_PROPERTY(QString logBg          READ logBg          NOTIFY themeChanged)
    Q_PROPERTY(QString popupBg        READ popupBg        NOTIFY themeChanged)
    Q_PROPERTY(QString popupHeaderBg  READ popupHeaderBg  NOTIFY themeChanged)

    // Borders / dividers
    Q_PROPERTY(QString divider            READ divider            NOTIFY themeChanged)
    Q_PROPERTY(QString borderColor        READ borderColor        NOTIFY themeChanged)
    Q_PROPERTY(QString inputBorderColor   READ inputBorderColor   NOTIFY themeChanged)
    Q_PROPERTY(QString inputBorderFocus   READ inputBorderFocus   NOTIFY themeChanged)
    Q_PROPERTY(QString popupBorderColor   READ popupBorderColor   NOTIFY themeChanged)
    Q_PROPERTY(QString popupHeaderBorder  READ popupHeaderBorder  NOTIFY themeChanged)
    Q_PROPERTY(QString frameBorderActive  READ frameBorderActive  NOTIFY themeChanged)
    Q_PROPERTY(QString frameBorderInact   READ frameBorderInact   NOTIFY themeChanged)

    // Text
    Q_PROPERTY(QString textPrimary    READ textPrimary    NOTIFY themeChanged)
    Q_PROPERTY(QString textSecondary  READ textSecondary  NOTIFY themeChanged)
    Q_PROPERTY(QString textMuted      READ textMuted      NOTIFY themeChanged)
    Q_PROPERTY(QString textDim        READ textDim        NOTIFY themeChanged)
    Q_PROPERTY(QString dialogLabel    READ dialogLabel    NOTIFY themeChanged)

    // Status
    Q_PROPERTY(QString successText  READ successText  NOTIFY themeChanged)
    Q_PROPERTY(QString successBg    READ successBg    NOTIFY themeChanged)
    Q_PROPERTY(QString errorText    READ errorText    NOTIFY themeChanged)
    Q_PROPERTY(QString errorBg      READ errorBg      NOTIFY themeChanged)
    Q_PROPERTY(QString errorBorder  READ errorBorder  NOTIFY themeChanged)

    // Accent
    Q_PROPERTY(QString accent         READ accent         NOTIFY themeChanged)
    Q_PROPERTY(QString accentHover    READ accentHover    NOTIFY themeChanged)
    Q_PROPERTY(QString accentPressed  READ accentPressed  NOTIFY themeChanged)

    // Buttons
    Q_PROPERTY(QString btnPrimaryBg      READ btnPrimaryBg      NOTIFY themeChanged)
    Q_PROPERTY(QString btnPrimaryHover   READ btnPrimaryHover   NOTIFY themeChanged)
    Q_PROPERTY(QString btnPrimaryPrs     READ btnPrimaryPrs     NOTIFY themeChanged)
    Q_PROPERTY(QString btnPrimaryText    READ btnPrimaryText    NOTIFY themeChanged)
    Q_PROPERTY(QString btnSecondaryBg    READ btnSecondaryBg    NOTIFY themeChanged)
    Q_PROPERTY(QString btnSecondaryHov   READ btnSecondaryHov   NOTIFY themeChanged)
    Q_PROPERTY(QString btnSecondaryText  READ btnSecondaryText  NOTIFY themeChanged)
    Q_PROPERTY(QString btnDangerBg       READ btnDangerBg       NOTIFY themeChanged)
    Q_PROPERTY(QString btnDangerHov      READ btnDangerHov      NOTIFY themeChanged)
    Q_PROPERTY(QString btnDangerPrs      READ btnDangerPrs      NOTIFY themeChanged)
    Q_PROPERTY(QString btnDangerText     READ btnDangerText     NOTIFY themeChanged)

    // Item states
    Q_PROPERTY(QString highlight  READ highlight  NOTIFY themeChanged)
    Q_PROPERTY(QString hoverBg    READ hoverBg    NOTIFY themeChanged)

    // Chat
    Q_PROPERTY(QString chatUserBubble  READ chatUserBubble  NOTIFY themeChanged)
    Q_PROPERTY(QString chatUserText    READ chatUserText    NOTIFY themeChanged)
    Q_PROPERTY(QString chatAsstBubble  READ chatAsstBubble  NOTIFY themeChanged)
    Q_PROPERTY(QString chatAsstText    READ chatAsstText    NOTIFY themeChanged)

    // Misc
    Q_PROPERTY(QString splitterNormal  READ splitterNormal  NOTIFY themeChanged)
    Q_PROPERTY(QString splitterHover   READ splitterHover   NOTIFY themeChanged)
    Q_PROPERTY(QString closeHoverBg    READ closeHoverBg    NOTIFY themeChanged)
    Q_PROPERTY(QString overlayColor    READ overlayColor    NOTIFY themeChanged)
    Q_PROPERTY(QString warnText        READ warnText        NOTIFY themeChanged)

public:
    explicit ThemeProvider(QObject *parent = nullptr);

    QString theme() const { return m_theme; }
    void setTheme(const QString &t);

    QString navBg()          const { return v("#181825","#dce0e8","#000000"); }
    QString baseBg()         const { return v("#1e1e2e","#eff1f5","#000000"); }
    QString surfaceBg()      const { return v("#181825","#e6e9ef","#0a0a0a"); }
    QString inputBg()        const { return v("#11111b","#ccd0da","#050505"); }
    QString titleBg()        const { return v("#11111b","#dce0e8","#000000"); }
    QString windowBg()       const { return v("#0b0b10","#dce0e8","#000000"); }
    QString logBg()          const { return v("#0f1020","#d0d4de","#000000"); }
    QString popupBg()        const { return v("#1b1d31","#e6e9ef","#0a0a0a"); }
    QString popupHeaderBg()  const { return v("#14162a","#dce0e8","#050505"); }

    QString divider()           const { return v("#313244","#bcc0cc","#1a1a1a"); }
    QString borderColor()       const { return v("#313244","#bcc0cc","#1a1a1a"); }
    QString inputBorderColor()  const { return v("#313244","#bcc0cc","#1a1a1a"); }
    QString inputBorderFocus()  const { return v("#89b4fa","#1e66f5","#89b4fa"); }
    QString popupBorderColor()  const { return v("#3a3f5c","#bcc0cc","#1a1a1a"); }
    QString popupHeaderBorder() const { return v("#333754","#bcc0cc","#1a1a1a"); }
    QString frameBorderActive() const { return v("#3f4360","#7c7f93","#2a2a2a"); }
    QString frameBorderInact()  const { return v("#2a2d41","#9ca0b0","#1a1a1a"); }

    QString textPrimary()   const { return v("#cdd6f4","#4c4f69","#ffffff"); }
    QString textSecondary() const { return v("#a6adc8","#5c5f77","#aaaaaa"); }
    QString textMuted()     const { return v("#585b70","#9ca0b0","#555555"); }
    QString textDim()       const { return v("#45475a","#acb0be","#333333"); }
    QString dialogLabel()   const { return v("#bac2de","#5c5f77","#cccccc"); }

    QString successText() const { return v("#a6e3a1","#40a02b","#44ff88"); }
    QString successBg()   const { return v("#1a3a1a","#d0f0d0","#001a00"); }
    QString errorText()   const { return v("#f38ba8","#d20f39","#ff4444"); }
    QString errorBg()     const { return v("#3a1a1a","#fce2da","#200000"); }
    QString errorBorder() const { return v("#f38ba8","#d20f39","#ff4444"); }

    QString accent()        const { return v("#89b4fa","#1e66f5","#89b4fa"); }
    QString accentHover()   const { return v("#74c7ec","#4285f4","#74c7ec"); }
    QString accentPressed() const { return v("#5e81ac","#1a56d5","#5e81ac"); }

    QString btnPrimaryBg()     const { return v("#89b4fa","#1e66f5","#89b4fa"); }
    QString btnPrimaryHover()  const { return v("#74c7ec","#4285f4","#74c7ec"); }
    QString btnPrimaryPrs()    const { return v("#5e81ac","#1a56d5","#5e81ac"); }
    QString btnPrimaryText()   const { return v("#1e1e2e","#ffffff","#000000"); }
    QString btnSecondaryBg()   const { return v("#313244","#ccd0da","#151515"); }
    QString btnSecondaryHov()  const { return v("#45475a","#bcc0cc","#252525"); }
    QString btnSecondaryText() const { return v("#a6adc8","#4c4f69","#aaaaaa"); }
    QString btnDangerBg()      const { return v("#f38ba8","#d20f39","#ff4444"); }
    QString btnDangerHov()     const { return v("#e33054","#b90020","#ee3333"); }
    QString btnDangerPrs()     const { return v("#a6192f","#8b0018","#cc2222"); }
    QString btnDangerText()    const { return v("#1e1e2e","#ffffff","#000000"); }

    QString highlight() const { return v("#313244","#ccd0da","#151515"); }
    QString hoverBg()   const { return v("#1e1e2e","#e6e9ef","#0d0d0d"); }

    QString chatUserBubble() const { return v("#2a2d5e","#c0cfff","#0a0a35"); }
    QString chatUserText()   const { return v("#b4c2ff","#1a3080","#b4c2ff"); }
    QString chatAsstBubble() const { return v("#181825","#e6e9ef","#0a0a0a"); }
    QString chatAsstText()   const { return v("#cdd6f4","#4c4f69","#ffffff"); }

    QString splitterNormal() const { return v("#2a2d41","#9ca0b0","#161616"); }
    QString splitterHover()  const { return v("#3b3f63","#7c7f93","#252525"); }
    QString closeHoverBg()   const { return v("#f38ba8","#d20f39","#ff4444"); }
    QString overlayColor()   const { return v("#90090b14","#60000000","#90000000"); }
    QString warnText()       const { return v("#f9e2af","#df8e1d","#ffcc44"); }

signals:
    void themeChanged();

private:
    QString m_theme;
    inline QString v(const char *dark, const char *light, const char *oled) const {
        if (m_theme == QLatin1String("light")) return QLatin1String(light);
        if (m_theme == QLatin1String("oled"))  return QLatin1String(oled);
        return QLatin1String(dark);
    }
};
