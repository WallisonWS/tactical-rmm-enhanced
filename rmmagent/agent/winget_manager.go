package agent

import (
	"fmt"
	"runtime"
	"strings"
	"time"
)

type WingetPackage struct {
	Name             string `json:"name"`
	ID               string `json:"id"`
	InstalledVersion string `json:"installed_version"`
	AvailableVersion string `json:"available_version"`
	Source           string `json:"source"`
}

type WingetOperationResult struct {
	Operation  string          `json:"operation"`
	PackageID  string          `json:"package_id,omitempty"`
	Success    bool            `json:"success"`
	Output     string          `json:"output"`
	Upgradable []WingetPackage `json:"upgradable,omitempty"`
	Timestamp  string          `json:"timestamp"`
}

// ListUpgradablePackages lists packages that have available updates using Winget (Windows), apt/dnf (Linux), or brew (macOS).
func (a *Agent) ListUpgradablePackages() WingetOperationResult {
	res := WingetOperationResult{
		Operation:  "list_upgradable",
		Upgradable: make([]WingetPackage, 0),
		Timestamp:  time.Now().UTC().Format(time.RFC3339),
	}

	if runtime.GOOS == "windows" {
		out, err := CMD("winget.exe", []string{"upgrade", "--accept-source-agreements", "--disable-interactivity"}, 45, false)
		if err != nil {
			res.Success = false
			res.Output = fmt.Sprintf("winget error: %v", err)
			return res
		}
		res.Success = true
		res.Output = out[0]
		res.Upgradable = parseWingetUpgradeTable(out[0])
		return res
	}

	// Linux fallback
	out, err := CMD("apt", []string{"list", "--upgradable"}, 30, false)
	if err == nil {
		res.Success = true
		res.Output = out[0]
		lines := strings.Split(out[0], "\n")
		for _, line := range lines {
			if strings.Contains(line, "/") && strings.Contains(line, "[upgradable") {
				parts := strings.Fields(line)
				if len(parts) >= 2 {
					name := strings.Split(parts[0], "/")[0]
					res.Upgradable = append(res.Upgradable, WingetPackage{
						Name:             name,
						ID:               name,
						AvailableVersion: parts[1],
						Source:           "apt",
					})
				}
			}
		}
	}
	return res
}

func parseWingetUpgradeTable(raw string) []WingetPackage {
	pkgs := make([]WingetPackage, 0)
	lines := strings.Split(raw, "\n")
	headerPassed := false
	for _, rLine := range lines {
		line := strings.TrimSpace(rLine)
		if line == "" {
			continue
		}
		if strings.HasPrefix(line, "---") {
			headerPassed = true
			continue
		}
		if !headerPassed {
			continue
		}
		if strings.Contains(line, "upgrades available") {
			break
		}
		fields := strings.Fields(line)
		if len(fields) >= 4 {
			src := fields[len(fields)-1]
			availVer := fields[len(fields)-2]
			instVer := fields[len(fields)-3]
			pkgID := fields[len(fields)-4]
			name := strings.Join(fields[:len(fields)-4], " ")
			if name == "" {
				name = pkgID
			}
			pkgs = append(pkgs, WingetPackage{
				Name:             name,
				ID:               pkgID,
				InstalledVersion: instVer,
				AvailableVersion: availVer,
				Source:           src,
			})
		}
	}
	return pkgs
}

// InstallWithWinget installs a specific package silently via Winget (Windows) or native package manager.
func (a *Agent) InstallWithWinget(packageID string) WingetOperationResult {
	res := WingetOperationResult{
		Operation: "install",
		PackageID: packageID,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}
	if strings.TrimSpace(packageID) == "" {
		res.Output = "missing package_id"
		return res
	}

	if runtime.GOOS == "windows" {
		args := []string{
			"install",
			"--id", packageID,
			"--exact",
			"--silent",
			"--accept-package-agreements",
			"--accept-source-agreements",
			"--disable-interactivity",
		}
		out, err := CMD("winget.exe", args, 300, false)
		res.Success = err == nil
		res.Output = strings.TrimSpace(out[0] + "\n" + out[1])
		return res
	}

	out, err := CMD("apt-get", []string{"install", "-y", packageID}, 300, false)
	res.Success = err == nil
	res.Output = strings.TrimSpace(out[0] + "\n" + out[1])
	return res
}

// UpgradeAllPackages upgrades either a specific package or all outdated packages silently.
func (a *Agent) UpgradeAllPackages(packageID string) WingetOperationResult {
	res := WingetOperationResult{
		Operation: "upgrade",
		PackageID: packageID,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}

	if runtime.GOOS == "windows" {
		args := []string{"upgrade"}
		if strings.TrimSpace(packageID) != "" && packageID != "all" {
			args = append(args, "--id", packageID, "--exact")
		} else {
			args = append(args, "--all")
		}
		args = append(args,
			"--silent",
			"--accept-package-agreements",
			"--accept-source-agreements",
			"--disable-interactivity",
		)
		out, err := CMD("winget.exe", args, 600, false)
		res.Success = err == nil
		res.Output = strings.TrimSpace(out[0] + "\n" + out[1])
		return res
	}

	out, err := CMD("apt-get", []string{"upgrade", "-y"}, 600, false)
	res.Success = err == nil
	res.Output = strings.TrimSpace(out[0] + "\n" + out[1])
	return res
}
