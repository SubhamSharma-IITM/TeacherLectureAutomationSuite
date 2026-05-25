/******************************************************************************
 * Acadza Studio — resumable upload to teacher portal.
 ******************************************************************************/
#include "OBSBasic.hpp"

#include <OBSApp.hpp>
#include <qt-wrappers.hpp>
#include <util/base.h>

#include <utility/RemoteTextThread.hpp>

#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QProgressDialog>
#include <QThread>

#include <atomic>
#include <functional>
#include <memory>

namespace {

constexpr int kChunkSize = 5 * 1024 * 1024;
constexpr int kFileWaitMs = 90000;
constexpr int kStablePollMs = 400;
constexpr int kStableRequired = 3;

using CancelFlag = std::shared_ptr<std::atomic<bool>>;

QString configString(const char *key, const QString &fallback = QString())
{
	const char *v = config_get_string(App()->GetUserConfig(), "Acadza", key);
	if (!v || !*v)
		return fallback;
	return QString::fromUtf8(v).trimmed();
}

bool isCanceled(const CancelFlag &canceled)
{
	return canceled && canceled->load();
}

/** Wait until the recorded file exists and size is stable (upload .mkv/.mp4 as saved). */
QString waitForStableUploadPath(const QString &rawPath, const CancelFlag &canceled,
				const std::function<void(const QString &)> &onStatus)
{
	if (rawPath.isEmpty())
		return QString();

	QFileInfo rawInfo(rawPath);
	QString candidate = rawInfo.absoluteFilePath();

	qint64 lastSize = -1;
	int stable = 0;
	int elapsed = 0;

	while (elapsed < kFileWaitMs) {
		if (isCanceled(canceled))
			return QString();

		QFileInfo info(candidate);
		if (info.exists() && info.isFile() && info.size() > 0) {
			if (onStatus) {
				onStatus(QTStr("Acadza.Upload.WaitingFile")
						 .arg(info.fileName())
						 .arg(elapsed / 1000));
			}
			if (info.size() == lastSize) {
				stable++;
				if (stable >= kStableRequired) {
					blog(LOG_INFO, "Acadza upload: file ready (%s, %lld bytes)",
					     info.fileName().toUtf8().constData(),
					     (long long)info.size());
					return info.absoluteFilePath();
				}
			} else {
				stable = 0;
				lastSize = info.size();
			}
		} else if (onStatus) {
			onStatus(QTStr("Acadza.Upload.WaitingFile").arg(
				QFileInfo(candidate).fileName(), elapsed / 1000));
		}

		QThread::msleep(kStablePollMs);
		elapsed += kStablePollMs;
	}

	return QString();
}

struct HttpResult {
	long status = 0;
	std::string body;
	std::string error;
	bool ok = false;
};

HttpResult portalHttpPost(const QString &url, const QByteArray &body,
			  const char *contentType,
			  const std::vector<std::string> &extraHeaders,
			  const CancelFlag &canceled)
{
	HttpResult result;
	if (isCanceled(canceled)) {
		result.error = "Upload canceled.";
		return result;
	}

	std::string response;
	std::string error;
	long code = 0;

	const bool failOnError = false;
	const int postSize = body.isEmpty() ? 0 : body.size();

	if (!GetRemoteFile(url.toUtf8().constData(), response, error, &code, contentType, "POST",
			   postSize > 0 ? body.constData() : "{}", extraHeaders, nullptr, 0,
			   failOnError, postSize)) {
		result.error = error.empty() ? "HTTP request failed" : error;
		result.status = code;
		return result;
	}

	result.status = code;
	result.body = response;
	result.ok = code >= 200 && code < 300;
	return result;
}

QString parseJsonError(const std::string &body, const QString &fallback)
{
	const QJsonDocument doc =
		QJsonDocument::fromJson(QByteArray::fromStdString(body));
	if (!doc.isObject())
		return fallback;
	const QString err = doc.object().value(QStringLiteral("error")).toString();
	return err.isEmpty() ? fallback : err;
}

bool uploadRecordingImpl(const QString &portalBase, const QString &filePath,
			 const QString &subject, const QString &chapter,
			 const CancelFlag &canceled,
			 const std::function<void(int)> &onProgress,
			 const std::function<void(const QString &)> &onStatus,
			 QString &errorOut)
{
	if (isCanceled(canceled)) {
		errorOut = QStringLiteral("Upload canceled.");
		return false;
	}

	QFileInfo fi(filePath);
	if (!fi.exists() || !fi.isFile()) {
		errorOut = QStringLiteral("Recording file not found: %1").arg(filePath);
		return false;
	}

	const qint64 fileSize = fi.size();
	if (fileSize <= 0) {
		errorOut = QStringLiteral("Recording file is empty.");
		return false;
	}

	QString mime = QStringLiteral("video/mp4");
	if (fi.suffix().compare(QLatin1String("mov"), Qt::CaseInsensitive) == 0)
		mime = QStringLiteral("video/quicktime");
	else if (fi.suffix().compare(QLatin1String("mkv"), Qt::CaseInsensitive) == 0)
		mime = QStringLiteral("video/x-matroska");

	const QString lectureTitle = fi.completeBaseName();
	const QString fileName = fi.fileName();

	if (onStatus)
		onStatus(QTStr("Acadza.Upload.Starting"));

	/* --- init --- */
	QJsonObject initObj;
	initObj.insert(QStringLiteral("fileName"), fileName);
	initObj.insert(QStringLiteral("mimeType"), mime);
	initObj.insert(QStringLiteral("fileSize"), fileSize);
	initObj.insert(QStringLiteral("lectureTitle"), lectureTitle);
	if (!subject.isEmpty())
		initObj.insert(QStringLiteral("subject"), subject);
	if (!chapter.isEmpty())
		initObj.insert(QStringLiteral("chapter"), chapter);
	initObj.insert(QStringLiteral("idempotencyKey"),
		       QStringLiteral("%1-%2-%3")
			       .arg(fileName)
			       .arg(fileSize)
			       .arg(fi.lastModified().toSecsSinceEpoch()));

	const QString initUrl = portalBase + QStringLiteral("/api/obs/upload/init");
	const QByteArray initPayload =
		QJsonDocument(initObj).toJson(QJsonDocument::Compact);

	blog(LOG_INFO, "Acadza upload: POST %s", initUrl.toUtf8().constData());

	const HttpResult initRes =
		portalHttpPost(initUrl, initPayload, "application/json", {}, canceled);

	if (isCanceled(canceled)) {
		errorOut = QStringLiteral("Upload canceled.");
		return false;
	}
	if (!initRes.ok) {
		errorOut = parseJsonError(initRes.body,
					  QStringLiteral("Upload init failed (HTTP %1)")
						  .arg(initRes.status));
		blog(LOG_WARNING, "Acadza upload init failed: %s", errorOut.toUtf8().constData());
		return false;
	}

	const QJsonDocument initDoc =
		QJsonDocument::fromJson(QByteArray::fromStdString(initRes.body));
	const QString jobId = initDoc.object().value(QStringLiteral("jobId")).toString();
	if (jobId.isEmpty()) {
		errorOut = QStringLiteral("Upload init returned no jobId");
		return false;
	}

	blog(LOG_INFO, "Acadza upload: jobId=%s", jobId.toUtf8().constData());

	/* --- chunks --- */
	QFile file(filePath);
	if (!file.open(QIODevice::ReadOnly)) {
		errorOut = QStringLiteral("Cannot open recording for read.");
		return false;
	}

	qint64 start = 0;
	while (start < fileSize) {
		if (isCanceled(canceled)) {
			errorOut = QStringLiteral("Upload canceled.");
			return false;
		}

		const qint64 end = std::min(start + (qint64)kChunkSize, fileSize) - 1;
		const qint64 len = end - start + 1;
		QByteArray chunk = file.read(len);
		if (chunk.size() != len) {
			errorOut = QStringLiteral("Failed to read recording chunk.");
			return false;
		}

		const QString chunkUrl =
			portalBase + QStringLiteral("/api/upload/") + jobId +
			QStringLiteral("/chunk");

		std::vector<std::string> headers;
		headers.push_back("Content-Type: application/octet-stream");
		headers.push_back(
			std::string("Content-Range: bytes ") + std::to_string(start) + "-" +
			std::to_string(end) + "/" + std::to_string(fileSize));

		const HttpResult chunkRes =
			portalHttpPost(chunkUrl, chunk, nullptr, headers, canceled);

		if (isCanceled(canceled)) {
			errorOut = QStringLiteral("Upload canceled.");
			return false;
		}
		if (!chunkRes.ok) {
			errorOut = parseJsonError(
				chunkRes.body,
				QStringLiteral("Chunk upload failed (HTTP %1)")
					.arg(chunkRes.status));
			return false;
		}

		const QJsonDocument chunkDoc =
			QJsonDocument::fromJson(QByteArray::fromStdString(chunkRes.body));
		const QJsonObject chunkJson = chunkDoc.object();
		const int progress =
			chunkJson.value(QStringLiteral("progressPercent")).toInt(0);
		if (onProgress)
			onProgress(progress);

		if (chunkJson.value(QStringLiteral("complete")).toBool()) {
			if (onProgress)
				onProgress(90);
			break;
		}

		start = end + 1;
	}

	if (isCanceled(canceled)) {
		errorOut = QStringLiteral("Upload canceled.");
		return false;
	}

	/* --- finalize --- */
	const QString finUrl = portalBase + QStringLiteral("/api/upload/") + jobId +
			       QStringLiteral("/finalize");
	const QByteArray finBody = QByteArray("{\"recipients\":[]}");

	blog(LOG_INFO, "Acadza upload: finalize %s", finUrl.toUtf8().constData());

	const HttpResult finRes =
		portalHttpPost(finUrl, finBody, "application/json", {}, canceled);

	if (isCanceled(canceled)) {
		errorOut = QStringLiteral("Upload canceled.");
		return false;
	}
	if (!finRes.ok) {
		errorOut = parseJsonError(finRes.body,
					  QStringLiteral("Finalize failed (HTTP %1)")
						  .arg(finRes.status));
		return false;
	}

	if (onProgress)
		onProgress(100);
	return true;
}

} // namespace

void OBSBasic::AcadzaCancelUpload()
{
	if (acadzaUploadCanceled)
		acadzaUploadCanceled->store(true);
	if (acadzaUploadThread)
		acadzaUploadThread->requestInterruption();
}

void OBSBasic::AcadzaStartUpload(const QString &rawRecordingPath)
{
	AcadzaCancelUpload();

	acadzaUploadCanceled = std::make_shared<std::atomic<bool>>(false);
	const CancelFlag canceled = acadzaUploadCanceled;

	const QString portal = AcadzaPortalBaseUrl();
	const QString subject = configString("DefaultSubject");
	const QString chapter = configString("DefaultChapter");

	blog(LOG_INFO, "Acadza upload: starting for %s -> %s",
	     rawRecordingPath.toUtf8().constData(), portal.toUtf8().constData());

	auto *progress = new QProgressDialog(QTStr("Acadza.Upload.Preparing"), QTStr("Cancel"),
					     0, 100, this);
	progress->setWindowTitle(QTStr("Acadza.Upload.Title"));
	progress->setWindowModality(Qt::WindowModal);
	progress->setMinimumDuration(0);
	progress->setAutoClose(false);
	progress->setAutoReset(false);
	progress->setValue(0);
	progress->show();

	QPointer<QProgressDialog> progressGuard(progress);
	QPointer<OBSBasic> self(this);

	auto triggerCancel = [this, canceled]() {
		if (canceled)
			canceled->store(true);
		AcadzaCancelUpload();
	};

	connect(progress, &QProgressDialog::canceled, this, triggerCancel);
	connect(progress, &QDialog::rejected, this, triggerCancel);

	QThread *thread = QThread::create([self, progressGuard, canceled, portal, subject, chapter,
					   rawRecordingPath]() {
		QString error;
		bool ok = false;
		bool wasCanceled = false;

		auto onStatus = [canceled, progressGuard](const QString &text) {
			if (isCanceled(canceled) || !progressGuard)
				return;
			QMetaObject::invokeMethod(
				progressGuard.data(),
				[progressGuard, text]() {
					if (progressGuard)
						progressGuard->setLabelText(text);
				},
				Qt::QueuedConnection);
		};

		auto onProgress = [canceled, progressGuard](int pct) {
			if (isCanceled(canceled) || !progressGuard)
				return;
			QMetaObject::invokeMethod(
				progressGuard.data(),
				[progressGuard, pct]() {
					if (progressGuard)
						progressGuard->setValue(pct);
				},
				Qt::QueuedConnection);
		};

		const QString filePath =
			waitForStableUploadPath(rawRecordingPath, canceled, onStatus);

		if (isCanceled(canceled)) {
			wasCanceled = true;
		} else if (filePath.isEmpty()) {
			error = QStringLiteral(
				"Recording file not ready. Wait for remux to finish or try again.");
		} else {
			ok = uploadRecordingImpl(portal, filePath, subject, chapter, canceled,
						 onProgress, onStatus, error);
			wasCanceled = isCanceled(canceled);
		}

		if (!self)
			return;

		QMetaObject::invokeMethod(
			self.data(),
			[self, progressGuard, ok, error, wasCanceled]() {
				self->acadzaUploadThread = nullptr;

				if (progressGuard) {
					progressGuard->close();
					progressGuard->deleteLater();
				}

				if (wasCanceled)
					return;

				if (ok) {
					OBSMessageBox::information(
						self, QTStr("Acadza.Upload.Success.Title"),
						QTStr("Acadza.Upload.Success.Text"));
				} else {
					OBSMessageBox::warning(
						self, QTStr("Acadza.Upload.Fail.Title"),
						error.isEmpty()
							? QTStr("Acadza.Upload.Fail.Text")
							: error);
				}
			},
			Qt::QueuedConnection);
	});

	acadzaUploadThread = thread;
	connect(thread, &QThread::finished, thread, &QObject::deleteLater);
	connect(thread, &QThread::finished, this, [this]() { acadzaUploadThread = nullptr; });
	thread->start();
}
