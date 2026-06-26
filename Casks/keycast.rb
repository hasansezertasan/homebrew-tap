cask "keycast" do
  version "0.0.0"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"

  url "https://github.com/hasansezertasan/keycast/releases/download/v#{version}/keycast.dmg"
  name "keycast"
  desc "Cross-platform keystroke and mouse click visualizer built in Python"
  homepage "https://github.com/hasansezertasan/keycast"

  livecheck do
    url :url
    strategy :github_latest
  end

  # The .app is built on macos-15 (see keycast's release.yml), which sets the
  # bundle's effective minimum-macOS floor.
  depends_on macos: ">= :sequoia"

  app "keycast.app"

  caveats <<~EOS
    keycast needs Accessibility and Input Monitoring permission:
      System Settings > Privacy & Security > Accessibility / Input Monitoring
    On first launch, macOS Gatekeeper will block the unsigned app — right-click
    the app and choose Open once to approve it.
  EOS
end
