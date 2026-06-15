import click

from markdown_to_anki.services.anki import (
    ensure_models,
    import_medias,
    import_notes,
)
from markdown_to_anki.services.anki_api import AnkiApi


@click.group()
@click.option(
    "--folder",
    default=None,
    help="Path to markdown notes directory (overrides MD_FOLDER env / config file).",
)
@click.option(
    "--url",
    default=None,
    help="AnkiConnect URL (overrides ANKI_URL env / config file).",
)
@click.option(
    "--resources",
    default=None,
    help="Path to custom resources directory for card templates and styles.",
)
@click.pass_context
def cli(ctx, folder, url, resources):
    from markdown_to_anki import config as m2a_config
    from markdown_to_anki.helpers.path import set_resources_dir

    ctx.ensure_object(dict)
    if folder:
        ctx.obj["MD_FOLDER"] = folder
    if url:
        ctx.obj["ANKI_URL"] = url
    set_resources_dir(resources or m2a_config.RESOURCES_DIR)


@cli.command("init")
@click.argument("verb")
@click.pass_context
def init(ctx, verb):
    md_folder = ctx.obj.get("MD_FOLDER") if ctx.obj else None
    match verb:
        case "all":
            click.echo(ensure_models())
            click.echo("done.")
            click.echo("import medias")
            click.echo(import_medias(md_folder=md_folder))
            click.echo("import notes")
            click.echo(import_notes(md_folder=md_folder))
        case _:
            click.echo(click.style("wrong verb: {}".format(verb), fg="red"))


@cli.command("anki")
@click.argument("verb")
@click.pass_context
def anki(ctx, verb):
    md_folder = ctx.obj.get("MD_FOLDER") if ctx.obj else None
    anki_url = ctx.obj.get("ANKI_URL") if ctx.obj else None
    match verb:
        case "check":
            try:
                anki_api = AnkiApi(
                    **({"anki_uri": anki_url} if anki_url else {})
                )
                anki_api.version()
            except Exception:
                click.secho("Connection Refused", fg="red")
                return
            click.secho("Connection OK!", fg="green")
        case "sync":
            click.echo("import medias")
            click.echo(import_medias(md_folder=md_folder))
            click.echo("import notes")
            click.echo(import_notes(md_folder=md_folder))
            try:
                anki_api = AnkiApi(
                    **({"anki_uri": anki_url} if anki_url else {})
                )
                click.echo(anki_api.sync())
            except Exception:
                click.secho("Connection Refused", fg="red")
        case "init":
            click.echo(ensure_models())
            click.echo("done.")
        case "sync_web":
            try:
                anki_api = AnkiApi(
                    **({"anki_uri": anki_url} if anki_url else {})
                )
                click.echo(anki_api.sync())
            except Exception:
                click.secho("Connection Refused", fg="red")
                return
            click.secho("Connection OK!", fg="green")
        case _:
            click.echo(click.style("wrong verb: {}".format(verb), fg="red"))


if __name__ == "__main__":
    cli()
