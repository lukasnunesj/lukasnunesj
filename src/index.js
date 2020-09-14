#!/usr/bin/env node

'use strict'

const boxen = require('boxen')
const chalk = require('chalk')
const inquirer = require('inquirer')
const clear = require('clear')
const open = require('open')
const my_info = require('../lib/data')
const emoji = require('node-emoji')

clear()

const prompt = inquirer.createPromptModule()

const questions = [{
    type: 'list',
    name: 'action',
    message: 'What you want to do?',
    choices: [{
            name: `${emoji.get("envelope_with_arrow")} Send me an ${chalk.green.bold('email')}?`,
            value: () => {
                open('mailto:lukasnunesj@gmail.com')
                console.log('\nDone, see you soon.\n')
            }
        },
        {
            name: `${emoji.get("information_source")}  Get Information in ${chalk.yellow.bold("JSON format")}?`,
            value: () => {
                console.log(JSON.stringify(my_info));
            }
        },
        {
            name: `${emoji.get("x")} Just ${chalk.hex("#ff0000").bold("quit")}.`,
            value: () => {
                console.log(`Ok, bye. ${emoji.get("wave")} \n`)
            }
        }
    ]
}]

const data = {
    name: chalk.hex("#037bfc").bold(`       ${emoji.get(":man:")}${emoji.get("computer")} Lucas Nunes Joaquim`),
    handle: chalk.hex("#fff")('@lukasnunesj'),
    work: `${chalk.hex("#FF6600")('Junior Full-stack Developer at')} ${chalk.hex('#365EAE').bold('Kabum!')}`,
    npm: chalk.gray('https://npmjs.com/') + chalk.hex("#CB3837")('~lucasnunesj'),
    github: chalk.gray('https://github.com/') + chalk.green('lukasnunesj'),
    linkedin: chalk.gray('https://linkedin.com/in/') + chalk.hex("#0077B5")('lucasnunesjoaquim'),
    web: chalk.hex("#00f0ff")('https://lucasnunes.dev'),
    npx: chalk.red('npx') + ' ' + chalk.hex("#fff")('lucasnunesj'),
    labelWork: chalk.hex("#fff").bold(`       Work:`),
    labelnpm: chalk.hex("#fff").bold('        npm:'),
    labelGitHub: chalk.hex("#fff").bold('     GitHub:'),
    labelLinkedIn: chalk.hex("#fff").bold('   LinkedIn:'),
    labelWeb: chalk.hex("#fff").bold('        Web:'),
    labelCard: chalk.hex("#fff").bold('       Card:')
}

const me = boxen(
    [
        `${data.name} / ${data.handle}`,
        `${data.labelWork}  ${data.work}`,
        `${data.labelnpm}  ${data.npm}`,
        `${data.labelGitHub}  ${data.github}`,
        `${data.labelLinkedIn}  ${data.linkedin}`,
        `${data.labelWeb}  ${data.web}`,
        `${data.labelCard}  ${data.npx}`,
        `${chalk.white.italic(
      "Sou um curioso, um entusiasta e um estudante na maior parte do tempo."
    )}`,
        `${chalk.white.italic('Nas horas vagas eu escrevo codigo que outros podem ler.')}`
    ].join('\n'), {
        margin: 1,
        float: 'center',
        padding: 1,
        borderStyle: 'single',
        borderColor: 'green'
    }
)

console.log(me)
const tip = [
    `${emoji.get("bulb")}Dica: Tente ${chalk.cyanBright.bold('cmd/ctrl + click')} nos links acima ${emoji.get("point_up_2")}`,
    ''
].join('\n')
console.log(tip)

prompt(questions).then(answer => answer.action())
